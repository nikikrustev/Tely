"""Render B's Q&A FRAGMENTS to audio for the offline Ask (BUILD_PLAN Stage 6, file 43 §6). OWNER: A (potencialbg).

    python -m audiostands.answers --cut judge        # build_bundle also calls build()

Writes into web/public/replay/v1/<cut>/answers/:
    <sha>.mp3      one MP3 per fragment, named by SSML sha256, in the commentary's voice (same SSML builder and cache)
    cache.json     the sha cache's own index (real durations), so a rebuild makes 0 TTS calls
    index.json     {"voice", "style", "fragments": {id: {"file", "duration_ms"}}}, read by B's FragmentPlayer
index.json holds no text: the fragment list has every event line of the cut, so the browser only learns words
from the tools, which are clamped to the playhead (qa/fragments.py spoiler note).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

from audiostands.commentary.source import BUNDLE
from audiostands.commentary.ssml import DEFAULT_VOICE, build_ssml, ssml_sha256
from audiostands.commentary.tts import AzureSynthesiser, Synthesiser, TtsCache, TtsError, load_env

FOLDER = "answers"
STYLE = "calm"                 # answers are spoken to the fan over a ducked crowd (file 36 rule 4: short, clear)
STYLES = {"hold": "urgent"}    # "Hold that thought, watch this!" leans in; it still says THAT, never WHAT


def fragments_for(out_dir: Path) -> list[dict[str, str]]:
    """B's FRAGMENTS for the bundle in out_dir (the committed judge cut, or a test copy)."""
    # SEAM(A->B): audiostands.qa.FRAGMENTS ([{id, text}], TEAM_SPLIT.md "The seams" point 2). It is built at import
    # from the committed judge bundle; any other folder (tests, a fresh cut) goes through B's own build_fragments.
    from audiostands.qa import FRAGMENTS
    from audiostands.qa.bundle import JUDGE, load_bundle
    from audiostands.qa.fragments import STATIC, build_fragments

    if out_dir.resolve() == JUDGE.resolve() and len(FRAGMENTS) > len(STATIC):  # static only = no bundle at import
        return FRAGMENTS
    return build_fragments(load_bundle(out_dir))


def build(out_dir: Path, synth_factory: Callable[[], Synthesiser], voice: str = DEFAULT_VOICE,
          fragments: list[dict[str, str]] | None = None) -> dict:
    """Render every fragment (cached by SSML hash), write answers/index.json, and drop MP3s no fragment uses."""
    frags = fragments_for(out_dir) if fragments is None else fragments
    folder = out_dir / FOLDER
    cache = TtsCache(folder, synth_factory, index_name="cache.json")
    table: dict[str, dict] = {}
    for f in frags:
        ssml = build_ssml(f["text"], STYLES.get(f["id"], STYLE), voice)
        sha = ssml_sha256(ssml)
        ms = cache.ensure(sha, ssml, f["text"])
        table[f["id"]] = {"file": f"{sha}.mp3", "duration_ms": ms}
    used = {v["file"] for v in table.values()}
    stale = [p for p in folder.glob("*.mp3") if p.name not in used]
    for p in stale:  # a fragment's text or the voice changed: keep the bundle to what Ask can actually play
        p.unlink()
    cache.index = {k: v for k, v in cache.index.items() if f"{k}.mp3" in used}
    cache.save()
    # SEAM(A->B): B's FragmentPlayer (web/src/ask/ask.ts) reads raw.fragments[id].file, relative to answers/.
    body = {"voice": voice, "style": STYLE, "count": len(table), "fragments": table}
    (folder / "index.json").write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                                       newline="\n")
    return {"fragments": len(table), "clips": len(used), "tts_calls": cache.calls, "chars_text": cache.chars_text,
            "chars_ssml": cache.chars_ssml, "chars_total": sum(len(f["text"]) for f in frags), "pruned": len(stale)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render the offline Ask fragments to answers/")
    ap.add_argument("--cut", default="judge", choices=["judge"])
    ap.add_argument("--voice", help="default: TTS_VOICE from .env")
    args = ap.parse_args(argv)
    env = load_env()
    voice = args.voice or env.get("TTS_VOICE") or DEFAULT_VOICE
    try:
        rep = build(BUNDLE / args.cut, lambda: AzureSynthesiser(env), voice)
    except TtsError as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"answers: {rep['fragments']} fragments, {rep['clips']} clips, {rep['tts_calls']} TTS calls, "
          f"{rep['chars_text']} characters synthesised ({rep['chars_total']} in all), {rep['pruned']} stale removed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
