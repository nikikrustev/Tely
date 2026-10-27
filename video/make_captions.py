"""Build video/captions_sdh.srt for the demo video from the judge-cut bundle.

The match part of the video is cut from the judge-cut replay (EDIT below), so its captions come straight from the
data that made the sound: the commentary cue text (cues.en.radio.jsonl), the crowd captions A's build_bundle wrote
(captions_sdh.vtt), and the shot, net and haptic events in segments.json. Nothing is typed by hand except EXTRA.
voiceover.srt (the narrator) and takes.srt (the live Ask, refusal and listener takes, typed from the recordings,
optional until they exist) are merged in, so captions_sdh.srt is the one complete SDH track to burn in and upload.

If the edit changes, change EDIT and rerun:  python video/make_captions.py
CI checks the committed file is current:     python video/make_captions.py --check
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "web" / "public" / "replay" / "v1" / "judge"
VIDEO = ROOT / "video"
OUT = VIDEO / "captions_sdh.srt"
MAX_S = 115.0          # the video must stay under 1:55 (file 14)
MERGE_S = 0.6          # sounds this close together share one caption
SOUND_MIN_S = 2.0      # a sound caption stays up at least this long
RISE = 0.2             # crowd excitement up this much in 2 s reads as "[crowd rises]"

# (video start s, match from s, match to s): which stretch of the judge cut plays where in the video.
EDIT = [
    (0.0, 954.8, 966.8),    # opener: crowd bed in the dead-ball stoppage after the yellow card (no commentary)
    (20.0, 674.0, 684.6),   # hero: crowd rises, build-up 4 s before the header, "It's in the net... VAR"
    (30.6, 702.8, 707.9),   # hero: "The goal stands!" and the roar, after the VAR wait is cut
]
# Captions for things the edit does, not the match: (video from s, video to s, text).
EXTRA = [
    (0.0, 2.5, "[stadium crowd fades in]"),
    (30.6, 32.4, "(18 seconds later, after the VAR check)"),
]
EARCON = {"shot": "shot", "net": "ball hits the net", "save": "save", "whistle": "whistle", "tackle": "tackle"}
SIDED = {"shot", "save", "tackle"}


def side(x: float) -> str:
    """The listener sits on the halfway line; Reds attack to the right (meta.json, the Start announcement)."""
    return "left" if x < -17 else "right" if x > 17 else "centre"


def ts(s: float) -> str:
    ms = round(s * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def parse_ts(t: str) -> float:
    h, m, rest = t.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def read_srt(path: Path) -> list[tuple[float, float, str]]:
    if not path.is_file():
        return []
    out = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip()):
        lines = block.strip().splitlines()
        arrow = next(i for i, ln in enumerate(lines) if "-->" in ln)
        a, b = (parse_ts(x.strip()) for x in lines[arrow].split("-->"))
        out.append((a, b, " ".join(lines[arrow + 1:]).strip()))
    return out


def crowd_captions() -> list[tuple[float, float, str]]:
    """The crowd_* entries of A's captions_sdh.vtt, already worded as SDH ("[Navy end roars]")."""
    out = []
    for block in re.split(r"\n\s*\n", (BUNDLE / "captions_sdh.vtt").read_text(encoding="utf-8")):
        lines = block.strip().splitlines()
        if len(lines) >= 3 and lines[0].startswith("crowd_"):
            a, b = (parse_ts(x.strip()) for x in lines[1].split("-->"))
            out.append((a, b, " ".join(lines[2:])))
    return out


def match_captions() -> list[tuple[float, float, str]]:
    cues = [json.loads(ln) for ln in (BUNDLE / "cues.en.radio.jsonl").read_text(encoding="utf-8").splitlines() if ln]
    seg = json.loads((BUNDLE / "segments.json").read_text(encoding="utf-8"))
    seconds = {s["t"]: max(s["crowd"]["H"]["excitement"], s["crowd"]["A"]["excitement"])
               for g in seg["segments"] for s in g["seconds"]}
    crowd = crowd_captions()
    sounds: list[tuple[float, float, str]] = list(crowd)
    for g in seg["segments"]:
        for e in g["earcons"]:
            if e["kind"] in EARCON:
                word = EARCON[e["kind"]] + (f", {side(e['x'])}" if e["kind"] in SIDED else "")
                sounds.append((e["t"], e["t"] + SOUND_MIN_S, f"[{word}]"))
        for h in g["haptics"]:
            name = re.sub(r"(?<!^)([A-Z])", r" \1", h["tacton"]).lower()
            sounds.append((h["t"], h["t"] + SOUND_MIN_S, f"[phone pulses: {name}]"))
    last_rise = -1e9
    for t in sorted(seconds):
        roared = any(abs(c[0] - t) <= 1.5 for c in crowd)   # the crowd caption already says how it reacts
        if t - 2 in seconds and seconds[t] - seconds[t - 2] >= RISE and t - last_rise > 6 and not roared:
            sounds.append((float(t), t + SOUND_MIN_S, "[crowd rises]"))
            last_rise = t

    out: list[tuple[float, float, str]] = []
    for v0, a, b in EDIT:
        to_video = lambda t: round(v0 + t - a, 3)  # noqa: E731
        first_line = True
        for c in cues:
            t0, t1 = c["t_in"], c["t_in"] + c["ttl_ms"] / 1000
            if t1 <= a or t0 >= b:
                continue
            if t0 < a or t1 > b:
                print(f"warning: {c['cue_id']} is cut mid-line by the edit {a}-{b}", file=sys.stderr)
            text = c["text"]["radio"]
            out.append((to_video(max(t0, a)), to_video(min(t1, b)), ("AI COMMENTATOR: " if first_line else "") + text))
            first_line = False
        group: list[tuple[float, float, str]] = []
        for s in sorted((x for x in sounds if a <= x[0] < b), key=lambda x: (x[0], x[2].startswith("[phone"))):
            if group and s[0] - group[0][0] > MERGE_S:
                out.append(_group(group, to_video, b))
                group = []
            if s[2] not in (g[2] for g in group):
                group.append(s)
        if group:
            out.append(_group(group, to_video, b))
    return out


def _group(group: list[tuple[float, float, str]], to_video, clip_end: float) -> tuple[float, float, str]:
    t0 = group[0][0]
    t1 = min(max(max(g[1] for g in group), t0 + SOUND_MIN_S), clip_end)
    return (to_video(t0), to_video(t1), " ".join(g[2] for g in group))


def build() -> str:
    entries = match_captions() + list(EXTRA) + read_srt(VIDEO / "voiceover.srt") + read_srt(VIDEO / "takes.srt")
    entries.sort(key=lambda e: (e[0], e[1]))
    late = [e for e in entries if e[1] > MAX_S]
    if late:
        raise SystemExit(f"captions run past {MAX_S} s: {late}")
    return "\n".join(f"{i}\n{ts(a)} --> {ts(b)}\n{text}\n" for i, (a, b, text) in enumerate(entries, 1))


def main(argv: list[str]) -> int:
    text = build()
    if "--check" in argv:
        current = OUT.read_text(encoding="utf-8") if OUT.is_file() else ""
        if current != text:
            print("video/captions_sdh.srt is out of date: run python video/make_captions.py", file=sys.stderr)
            return 1
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({text.count(' --> ')} captions)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
