"""Turn the CC0 crowd recordings into the browser's crowd clips (BUILD_PLAN Stage 2). OWNER: B (Nikolay).

    pip install numpy soundfile lameenc          # tools for this script only (BSD, BSD + LGPL libsndfile, LGPL LAME)
    python scripts/prepare_crowd.py

Reads assets/raw/* and assets/crowd_sources.csv (id, file, author, url, licence, role, start, end), cuts each row's
[start, end], resamples to 44.1 kHz stereo, normalises the level (RMS, see LEVEL_DB), bakes a seamless loop into
beds, and writes web/public/crowd/<role>_<n>.mp3, web/public/crowd/manifest.json and assets/licences.json.

Refuses any row whose licence is not CC0 (CLAUDE.md; file 38 §4). If assets/raw is empty it writes generated
placeholder noise instead, so the browser still runs, and prints a warning.
Deviation from BUILD_PLAN: it uses LAME (lameenc, LGPL) instead of an LGPL ffmpeg build, which isn't installed here.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW, CSV = ROOT / "assets" / "raw", ROOT / "assets" / "crowd_sources.csv"
OUT, LICENCES = ROOT / "web" / "public" / "crowd", ROOT / "assets" / "licences.json"
SR = 44100
BEDS = {"murmur", "swell", "tense", "away"}
# Target RMS level per role (ours, a starting point; tune by ear). Beds sit under the one-shots.
LEVEL_DB = {"murmur": -24.0, "swell": -24.0, "tense": -26.0, "away": -28.0}
SHOT_DB, PEAK_DB, LOOP_XFADE_S, FADE_OUT_S = -20.0, -1.0, 1.0, 0.3


def is_cc0(licence: str) -> bool:
    return licence.strip().upper().replace(" ", "") in ("CC0", "CC0-1.0", "CC01.0")


def resample(x: np.ndarray, sr: int) -> np.ndarray:
    """FFT resampling per channel (fine for short clips; no SciPy needed)."""
    if sr == SR:
        return x
    n = int(round(len(x) * SR / sr))
    out = np.empty((n, x.shape[1]))
    for c in range(x.shape[1]):
        spec = np.fft.rfft(x[:, c])
        keep = min(len(spec), n // 2 + 1)
        new = np.zeros(n // 2 + 1, dtype=complex)
        new[:keep] = spec[:keep]
        out[:, c] = np.fft.irfft(new, n) * (n / len(x))
    return out


def level(x: np.ndarray, target_db: float) -> np.ndarray:
    rms = np.sqrt(np.mean(x ** 2)) + 1e-12
    y = x * (10 ** (target_db / 20) / rms)
    peak = np.max(np.abs(y)) + 1e-12
    limit = 10 ** (PEAK_DB / 20)
    return y * (limit / peak) if peak > limit else y


def loopable(x: np.ndarray) -> np.ndarray:
    """Equal-power crossfade of the last second into the first, so a looped bed has no seam."""
    k = int(LOOP_XFADE_S * SR)
    if len(x) <= 3 * k:
        return x
    w = np.linspace(0, np.pi / 2, k)[:, None]
    head = x[:k] * np.sin(w) + x[-k:] * np.cos(w)
    return np.concatenate([head, x[k:-k]])


def fade(x: np.ndarray) -> np.ndarray:
    k_in, k_out = int(0.01 * SR), int(FADE_OUT_S * SR)
    x = x.copy()
    x[:k_in] *= np.linspace(0, 1, k_in)[:, None]
    x[-k_out:] *= np.linspace(1, 0, k_out)[:, None]
    return x


def mp3(x: np.ndarray, path: Path) -> None:
    import lameenc
    enc = lameenc.Encoder()
    enc.set_bit_rate(128)
    enc.set_in_sample_rate(SR)
    enc.set_channels(2)
    enc.set_quality(2)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    path.write_bytes(bytes(enc.encode(pcm) + enc.flush()))


def placeholder(role: str) -> np.ndarray:
    """Generated noise so the app runs before any CC0 clip exists (never shipped as 'crowd')."""
    rng = np.random.default_rng(abs(hash(role)) % 2 ** 32)
    secs = 20.0 if role in BEDS else 3.0
    n = int(secs * SR)
    noise = np.cumsum(rng.standard_normal((n, 2)), axis=0)       # brown-ish noise, crowd-like rumble
    noise -= np.linspace(noise[0], noise[-1], n)
    env = np.ones((n, 1)) if role in BEDS else np.exp(-np.linspace(0, 4, n))[:, None]
    return noise * env


def main() -> int:
    import soundfile as sf
    rows = list(csv.DictReader(CSV.open(encoding="utf-8"))) if CSV.exists() else []
    bad = [r for r in rows if not is_cc0(r["licence"])]
    if bad:
        for r in bad:
            print(f"REFUSED {r['file']}: licence {r['licence']!r} is not CC0", file=sys.stderr)
        return 1
    have = RAW.exists() and any(p.is_file() for p in RAW.iterdir())
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.mp3"):
        old.unlink()
    manifest: dict[str, list[str]] = {}
    licences = []
    if not have:
        print("WARNING: assets/raw is empty -> writing generated placeholder noise, not real crowd clips")
        for role in sorted(BEDS | {"roar", "ooh_groan", "relief_applause", "whistles_jeer", "cheer"}):
            name = f"{role}_1.mp3"
            x = placeholder(role)
            mp3(level(loopable(x) if role in BEDS else fade(x), LEVEL_DB.get(role, SHOT_DB)), OUT / name)
            manifest[role] = [name]
        (OUT / "manifest.json").write_text(json.dumps({"placeholder": True, "roles": manifest}, indent=2) + "\n",
                                           encoding="utf-8", newline="\n")
        return 0
    for r in rows:
        x, sr = sf.read(RAW / r["file"], always_2d=True)
        a, b = int(float(r["start"]) * sr), int(float(r["end"]) * sr)
        x = x[a:min(b, len(x))]
        if x.shape[1] == 1:
            x = np.repeat(x, 2, axis=1)
        x = resample(x[:, :2].astype(float), sr)
        role = r["role"]
        x = level(loopable(x) if role in BEDS else fade(x), LEVEL_DB.get(role, SHOT_DB))
        n = len(manifest.setdefault(role, [])) + 1
        name = f"{role}_{n}.mp3"
        mp3(x, OUT / name)
        manifest[role].append(name)
        licences.append(dict(output=f"web/public/crowd/{name}", freesound_id=r["id"], author=r["author"], url=r["url"],
                             licence="CC0-1.0", role=role, cut_s=[float(r["start"]), float(r["end"])],
                             notes=r.get("notes", "")))
        print(f"{name:24s} <- {r['file']:18s} {len(x) / SR:5.1f} s  {r['url']}")
    (OUT / "manifest.json").write_text(json.dumps({"placeholder": False, "roles": manifest}, indent=2) + "\n",
                                       encoding="utf-8", newline="\n")
    LICENCES.write_text(json.dumps(licences, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(licences)} clips, all CC0 -> {OUT.relative_to(ROOT)}, {LICENCES.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
