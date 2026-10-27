"""Render relay/clips.py to MP3 in the commentary voice.

    python -m relay.render_clips            # from the repo root, PYTHONPATH=pipeline;.  (needs Azure Speech, A only)

Writes web/public/replay/v1/judge/live/: <ssml sha256>.mp3 per clip, cache.json, and index.json
{"voice", "clips": {id: {"file", "text", "duration_ms"}}}, which voice/live-ask.ts reads. Same SSML builder and hash cache
as the commentary and answers (Stage 3/6), so a rebuild makes 0 TTS calls and the refusal sounds like the commentator.
"""
from __future__ import annotations

import json
import sys

from tely.commentary.source import BUNDLE
from tely.commentary.ssml import DEFAULT_VOICE, build_ssml, ssml_sha256
from tely.commentary.tts import AzureSynthesiser, TtsCache, TtsError, load_env

from .clips import CLIPS

FOLDER = BUNDLE / "judge" / "live"
STYLE = "calm"


def build(voice: str, synth_factory) -> dict:
    cache = TtsCache(FOLDER, synth_factory, index_name="cache.json")
    table = {}
    for cid, text in CLIPS.items():
        ssml = build_ssml(text, STYLE, voice)
        sha = ssml_sha256(ssml)
        table[cid] = {"file": f"{sha}.mp3", "text": text, "duration_ms": cache.ensure(sha, ssml, text)}
    used = {v["file"] for v in table.values()}
    for p in FOLDER.glob("*.mp3"):
        if p.name not in used:
            p.unlink()
    cache.index = {k: v for k, v in cache.index.items() if f"{k}.mp3" in used}
    cache.save()
    (FOLDER / "index.json").write_text(json.dumps({"voice": voice, "clips": table}, indent=1, ensure_ascii=False) + "\n",
                                       encoding="utf-8", newline="\n")
    return {"clips": len(table), "tts_calls": cache.calls}


def main() -> int:
    env = load_env()
    voice = env.get("TTS_VOICE") or DEFAULT_VOICE
    try:
        rep = build(voice, lambda: AzureSynthesiser(env))
    except TtsError as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"live clips: {rep['clips']} clips, {rep['tts_calls']} TTS calls -> {FOLDER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
