"""Render the same 4 lines in 3 en-US DragonHD voices to out/voices/, so a person can pick TTS_VOICE by ear.

OWNER: A (potencialbg). Run on A's machine after `az login`:
    python -m tely.voices                     # TTS_VOICE from .env + two more
    python -m tely.voices --voices en-US-Davis:DragonHDLatestNeural,en-US-Emma:DragonHDLatestNeural
It uses the same SSML builder and hash cache as build_commentary, so a sample sounds exactly like the real track
and a re-run makes 0 TTS calls.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Callable

from tely.commentary.ssml import DEFAULT_VOICE, build_ssml, ssml_sha256
from tely.commentary.tts import ROOT, AzureSynthesiser, Synthesiser, TtsCache, TtsError, load_env

# All three are in the en-US DragonHD list our resource returned on 21 Oct 2026 (get_voices_async).
EXTRA_VOICES = ("en-US-Brian:DragonHDLatestNeural", "en-US-Ava:DragonHDLatestNeural",
                "en-US-Davis:DragonHDLatestNeural")
# (slug, style, pause after, text): build-up, goal call, miss, calm state line. Fictional players from contracts/b.
LINES = (
    ("1_buildup", "urgent", 0, "Attacking third, centre, Reds. Ilievski... Reds pushing, this could open up!"),
    ("2_goal", "shouting", 300, "Goal! Ndiaye-Ross! Reds one, Navy nil!"),
    ("3_miss", "excited", 300, "Wide! Just past the post, and Navy breathe again."),
    ("4_state", "calm", 0, "Midfield, near side, Navy in possession. Reds one, Navy nil, two minutes played."),
)


def pick_voices(env: dict[str, str], requested: str | None) -> list[str]:
    if requested:
        return [v.strip() for v in requested.split(",") if v.strip()]
    first = env.get("TTS_VOICE") or DEFAULT_VOICE
    return [first] + [v for v in EXTRA_VOICES if v != first][:2]


def slug(voice: str) -> str:
    return voice.split(":")[0].removeprefix("en-US-").lower()


def render(voices: list[str], out_dir: Path, synth_factory: Callable[[], Synthesiser]) -> tuple[list[Path], TtsCache]:
    cache = TtsCache(out_dir / "_cache", synth_factory)
    written = []
    for voice in voices:
        for name, style, pause, text in LINES:
            ssml = build_ssml(text, style, voice, pause_after_ms=pause)
            sha = ssml_sha256(ssml)
            cache.ensure(sha, ssml, text)
            dest = out_dir / f"{slug(voice)}_{name}.mp3"
            shutil.copyfile(cache.folder / f"{sha}.mp3", dest)
            written.append(dest)
    return written, cache


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--voices", help="comma-separated voice names (default: TTS_VOICE + two more)")
    ap.add_argument("--out", type=Path, default=ROOT / "out" / "voices")
    args = ap.parse_args(argv)
    env = load_env()
    voices = pick_voices(env, args.voices)
    try:
        written, cache = render(voices, args.out, lambda: AzureSynthesiser(env))
    except TtsError as exc:
        print(f"FAIL: {exc}")
        return 1
    for p in written:
        print(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p)
    print(f"{len(written)} files, {cache.calls} TTS calls, {cache.chars_text} characters synthesised. "
          f"Pick one by ear and set TTS_VOICE in .env.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
