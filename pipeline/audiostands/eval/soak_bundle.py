"""Full-length soak bundles: each half of the synthetic match (seed 24, the one the judge cut comes from) as its own
replay bundle, for the 90-minute live-readiness run (D24). OWNER: A (potencialbg).

    python -m audiostands.eval.soak_bundle            # both halves -> web/.local/soak1/ and web/.local/soak2/

WHY local only: web/.local/ is git-ignored and only the dev server serves it (/replay/v1/local/<stem>/, vite.config.ts),
so a 48-minute bundle never reaches the deployed site. The page opens it with /?bundle=soak1 on the dev server.
WHY a tone and not Azure TTS: the soak checks timing, memory and sessions, not the voice. ToneSynth writes a short
WAV tone per commentary line, its length taken from the words (about 2.6 words a second), so the commentary track
schedules, plays and is measurable (RMS) exactly as with real audio, with no Speech calls and no cost.
Everything else is the real pipeline: B's build_match and build_segments, the rules Director, A's build_commentary
(truth check and spoiler check included) and the manifest. The preset answers and live refusal clips are copied
from the judge bundle (same players, same voice).
"""
from __future__ import annotations

import io
import json
import math
import re
import shutil
import struct
import sys
import wave
from pathlib import Path

from audiostands import build_bundle, build_commentary, build_match, build_segments
from audiostands.commentary import source
from audiostands.commentary.source import load_match
from audiostands.commentary.ssml import DEFAULT_VOICE
from audiostands.generator import FPS, generate

ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / "web" / ".local"
JUDGE = ROOT / "web" / "public" / "replay" / "v1" / "judge"
SEED = 24
RATE = 8000
WORDS_PER_S = 2.6


class ToneSynth:
    """Synthesiser protocol (commentary/tts.py) with no service: a soft 330 Hz tone as long as the line would be."""

    def synthesise(self, ssml: str) -> tuple[bytes, float]:
        text = re.sub(r"<[^>]+>", " ", ssml)
        seconds = max(0.8, len(text.split()) / WORDS_PER_S)
        n = int(seconds * RATE)
        frames = bytearray()
        for i in range(n):
            env = min(1.0, i / 400, (n - i) / 400)          # 50 ms fades, no clicks
            frames += struct.pack("<h", int(6000 * env * math.sin(2 * math.pi * 330 * i / RATE)))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(bytes(frames))
        return buf.getvalue(), n / RATE                     # WAV bytes in a .mp3 name: browsers sniff the content


def build_half(k: int, out: Path) -> dict:
    m = generate(SEED)
    period = m["periods"][k]
    cut = {"seed": SEED, "period": period["period"], "t_start": 0, "t_end": int(period["end_f"] // FPS)}
    name = out.name
    if out.exists():
        shutil.rmtree(out)
    build_match.build(cut, out, report=False)                # SEAM(A->B): B's match files, full period
    source.MATCH_DIRS[name] = out                            # load_match(name) reads this bundle
    run, _ = build_bundle.run_director(name, out, ToneSynth, DEFAULT_VOICE, "rules", None)
    rep = build_commentary.build(name, out, ToneSynth, DEFAULT_VOICE, run.plans,
                                 {s.window.key: s.director for s in run.steps})
    build_segments.build(name, out)                          # SEAM(A->B): B's segments.json, full period
    for folder in ("answers", "live"):
        shutil.copytree(JUDGE / folder, out / folder)
    man = build_bundle.manifest(name, out, load_match(name), DEFAULT_VOICE, run.name)
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n", encoding="utf-8", newline="\n")
    return {"bundle": name, "period": cut["period"], "duration_s": cut["t_end"], "lines": rep["lines"],
            "truth_check": rep["truth_check_pass"], "spoiler_leaks": len(rep["spoiler_leaks"]),
            "failed": len(rep["failed"]), "chapters": len(man["chapters"]), "files": man["files"],
            "mb": round(man["bytes"] / 1e6, 1)}


def main() -> int:
    ok = True
    for k in (0, 1):
        r = build_half(k, LOCAL / f"soak{k + 1}")
        ok = ok and not r["spoiler_leaks"] and not r["failed"]
        print(json.dumps(r))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
