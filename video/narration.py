"""Optional: narrate video/voiceover.srt with Azure Speech, in a voice that isn't the commentator's.

record the voiceover yourself, or run this and approve it. Either way the end card labels the AI voices.
The commentator is en-US-Brian HD (D13), so the narrator defaults to en-US-Ava HD, which our resource lists (D9).

Writes, under out/ (git-ignored):
- out/narration/vo_NN.mp3: one file per voiceover cue, to drop on the editor's timeline at the cue's start time;
- out/narration.mp3: the whole voiceover on the video timeline, the gaps made with SSML breaks sized from the cue files.
HD voices sound slightly different on every render (D9), so the full track can drift from the cue files by a few
hundred ms; the cue files are the exact ones. A cue that runs past its slot is reported: trim the line or the slot.

Auth is keyless first, then SPEECH_KEY from .env (tely.commentary.tts); nothing prints a key.
Usage (A's machine): python video/narration.py [--voice NAME] [--srt FILE] [--out DIR] [--dry-run]
About 30 short HD TTS calls (one per cue, then one for the full track).
--srt/--out narrate another cue file, e.g. the infrastructure segment:
  python video/narration.py --srt video/voiceover_infra.srt --out out/narration_infra
writes out/narration_infra/vo_NN.mp3 and out/narration_infra.mp3.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "video"))

from tely.commentary.ssml import _SENTENCE, NS, TEMPERATURE, build_ssml  # noqa: E402
from make_captions import read_srt  # noqa: E402

VOICE = "en-US-Ava:DragonHDLatestNeural"
STYLE = "calm"
OUT = ROOT / "out"
MAX_BREAK_MS = 5000   # one <break> is capped; longer gaps chain several (our cap, kept under the service limit)
SLACK_S = 0.3         # how far a cue may run past its slot before we warn
SAY_AS = {"Tely": "Telly"}   # D26: say the name "telly", never "tee-lee"; the captions keep the written form


def spoken(text: str) -> str:
    for written, said in SAY_AS.items():
        text = text.replace(written, said)
    return text


def breaks(ms: int) -> str:
    out = []
    while ms > 0:
        out.append(f'<break time="{min(ms, MAX_BREAK_MS)}ms"/>')
        ms -= MAX_BREAK_MS
    return "".join(out)


def full_ssml(cues: list[tuple[float, float, str]], durations: list[float], voice: str) -> str:
    """The whole voiceover as one document: a break before each cue so it starts at its SRT time."""
    body, t = [], 0.0
    for (start, _, text), dur in zip(cues, durations):
        body.append(breaks(max(0, round((start - t) * 1000))))
        body.append(" ".join(f"[{STYLE}] {escape(s)}" for s in _SENTENCE.split(text.strip()) if s) + " ")
        t = max(start, t) + dur
    return (f'<speak {NS} xml:lang="en-US"><voice name="{escape(voice)}" parameters="temperature={TEMPERATURE}">'
            f'{"".join(body)}</voice></speak>')


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--voice", default=VOICE)
    ap.add_argument("--srt", type=Path, default=ROOT / "video" / "voiceover.srt", help="the cue file to narrate")
    ap.add_argument("--out", type=Path, default=OUT / "narration", help="folder for the cue files; the full track "
                    "goes next to it as <folder>.mp3")
    ap.add_argument("--dry-run", action="store_true", help="print the cues and SSML, call nothing")
    args = ap.parse_args(argv)
    if "Brian" in args.voice:
        print("warning: Brian is the commentator's voice; the plan asks for a different narrator voice", file=sys.stderr)
    cues = [(a, b, spoken(text)) for a, b, text in read_srt(args.srt)]
    if args.dry_run:
        for i, (a, b, text) in enumerate(cues, 1):
            print(f"vo_{i:02} {a:6.2f}-{b:6.2f} {build_ssml(text, STYLE, args.voice)}")
        return 0

    from tely.commentary.tts import AzureSynthesiser, TtsError, load_env

    try:
        synth = AzureSynthesiser(load_env())
        folder = args.out
        folder.mkdir(parents=True, exist_ok=True)
        durations = []
        for i, (a, b, text) in enumerate(cues, 1):
            mp3, dur = synth.synthesise(build_ssml(text, STYLE, args.voice))
            (folder / f"vo_{i:02}.mp3").write_bytes(mp3)
            durations.append(dur)
            over = dur - (b - a)
            flag = f"  OVER its slot by {over:.1f} s" if over > SLACK_S else ""
            print(f"vo_{i:02}.mp3  {a:6.2f} s  {dur:4.1f} s of speech in a {b - a:4.1f} s slot{flag}")
        mp3, dur = synth.synthesise(full_ssml(cues, durations, args.voice))
        full = folder.with_suffix(".mp3")
        full.write_bytes(mp3)
        print(f"{full.name}  {dur:.1f} s (last cue ends at {cues[-1][1]:.1f} s); auth: {synth.auth}")
    except TtsError as exc:
        print(f"narration failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
