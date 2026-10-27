"""Low-data commentary (Tier 2 item 11, D36): every track re-recorded at 16 kHz / 32 kbps mono, beside the normal one.

    python -m tely.commentary.lowdata --cut judge

Writes audio/<lang>/radio-lo/<sha>.mp3 (same names as audio/<lang>/radio/) and its index.json. The page uses them in
low-data mode (Save-Data, a 2G/3G connection, or the Setup switch). We record the exact same SSML: it is rebuilt the
way the build made it and must hash to the cue's ssml_sha256, else that line keeps its normal file. A low-data take
that would run past the next line's start is dropped too, so the low-data track never overlaps where the normal
one doesn't. The cue files don't change.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

from tely.commentary import languages as L
from tely.commentary.source import BUNDLE
from tely.commentary.ssml import build_ssml, ssml_sha256
from tely.commentary.tts import AzureSynthesiser, Synthesiser, TtsCache, TtsError, load_env

LOW_FMT = "Audio16Khz32KBitRateMonoMp3"
FOLDER = "radio-lo"
PAUSES = range(0, 2001, 10)   # the English build's pause_after_ms values (ms); we search for the one that hashes right


def rebuild_ssml(c: dict) -> str | None:
    """The SSML this cue was recorded from, or None if we can't reproduce it exactly."""
    u, text, sha = c["utterance"], c["text"]["radio"], c["utterance"]["ssml_sha256"]
    if u.get("lang", "en-US") == "en-US":
        for pause in PAUSES:
            ssml = build_ssml(text, u["style"], u["voice"], pause_after_ms=pause)
            if ssml_sha256(ssml) == sha:
                return ssml
        return None
    for extra in range(0, L.MAX_RATE + 1):
        ssml = L.build_ssml(text, u["lang"], u["intensity"], extra)
        if ssml_sha256(ssml) == sha:
            return ssml
    return None


def build(out_dir: Path, lang: str, synth_factory: Callable[[], Synthesiser]) -> dict:
    cues = [json.loads(s) for s in (out_dir / f"cues.{lang}.radio.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
    cues.sort(key=lambda c: c["t_in"])
    cache = TtsCache(out_dir / "audio" / lang / FOLDER, synth_factory)
    kept, skipped = set(), {"no_ssml": 0, "too_long": 0}
    t_end = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))["t_end"]
    for i, c in enumerate(cues):
        ssml = rebuild_ssml(c)
        if ssml is None:
            skipped["no_ssml"] += 1
            continue
        sha = c["utterance"]["ssml_sha256"]
        ms = cache.ensure(sha, ssml, c["text"]["radio"])
        room = ((cues[i + 1]["t_in"] if i + 1 < len(cues) else t_end) - c["t_in"]) * 1000
        if ms > max(room, c["utterance"]["duration_ms"]) and ms > c["utterance"]["duration_ms"] + 50:
            skipped["too_long"] += 1
            continue
        kept.add(sha)
    for sha in [s for s in cache.index if s not in kept]:   # only what the page may play
        (cache.folder / f"{sha}.mp3").unlink(missing_ok=True)
        del cache.index[sha]
    cache.save()
    normal = sum((out_dir / "audio" / lang / "radio" / f"{c['utterance']['ssml_sha256']}.mp3").stat().st_size for c in cues)
    low = sum((cache.folder / f"{s}.mp3").stat().st_size for s in kept)
    low += sum((out_dir / "audio" / lang / "radio" / f"{c['utterance']['ssml_sha256']}.mp3").stat().st_size
               for c in cues if c["utterance"]["ssml_sha256"] not in kept)
    return {"lang": lang, "lines": len(cues), "low": len(kept), **skipped, "tts_calls": cache.calls,
            "bytes_normal": normal, "bytes_low": low}


def main(argv: list[str] | None = None) -> int:
    from tely import build_bundle
    from tely.commentary.source import load_match

    ap = argparse.ArgumentParser(description="Low-data copies of every commentary track")
    ap.add_argument("--cut", default="judge")
    ap.add_argument("--langs", default="en," + ",".join(L.LANGS))
    args = ap.parse_args(argv)
    out_dir = BUNDLE / args.cut
    env = load_env()
    reports = []
    try:
        for lang in [s for s in args.langs.split(",") if s]:
            reports.append(build(out_dir, lang, lambda: AzureSynthesiser(env, fmt=LOW_FMT)))
            print(json.dumps(reports[-1]))
    except TtsError as exc:
        print(f"FAIL: {exc}")
        return 1
    (out_dir / "lowdata.json").write_text(json.dumps({"format": LOW_FMT, "tracks": reports}, indent=1) + "\n",
                                           encoding="utf-8", newline="\n")
    old = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    man = build_bundle.manifest(args.cut, out_dir, load_match(args.cut), old["voice"], old.get("director"))
    (out_dir / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"PASS: {man['files']} files, {man['bytes'] / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
