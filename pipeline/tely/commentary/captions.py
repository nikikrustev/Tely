"""Cues -> captions_sdh.vtt and descriptions.vtt (files 32 §e and 42). OWNER: A (potencialbg).

captions_sdh.vtt: what a deaf viewer needs: the AI commentator's words plus the crowd sounds in [brackets].
descriptions.vtt (kind="descriptions"): the verified lines only, never overlapping (file 32 builder: a more
important line cuts the earlier one short; a less important one is dropped).
"""

from __future__ import annotations

from tely.commentary.source import Match

CROWD_WORDS = {"roar": "roars", "stunned_hush": "falls silent", "ooh_groan": "groans",
               "relief_applause": "applauds in relief"}
CROWD_CAPTION_S = 2.5


def ts(sec: float) -> str:
    ms = round(sec * 1000)
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _end(c: dict) -> float:
    return c["t_in"] + c["utterance"]["duration_ms"] / 1000


def captions_sdh(cues: list[dict], m: Match) -> str:
    items = []
    for i, c in enumerate(cues):
        speaker = "AI COMMENTATOR: " if i == 0 else ""
        items.append((c["t_in"], _end(c), c["cue_id"], speaker + c["text"]["radio"]))
    for k, o in enumerate(m.signals.get("crowd_one_shots", [])):
        side = "home" if o["end"] == "H" else "away"
        what = CROWD_WORDS.get(o["kind"], o["kind"].replace("_", " "))
        items.append((o["t"], o["t"] + CROWD_CAPTION_S, f"crowd_{k + 1:03d}", f"[{m.team_name(side)} end {what}]"))
    lines = ["WEBVTT", ""]
    for start, end, cid, text in sorted(items):
        lines += [cid, f"{ts(start)} --> {ts(end)}", text, ""]
    return "\n".join(lines)


def descriptions(cues: list[dict]) -> str:
    kept: list[list] = []  # [start, end, prio, cue_id, text]
    for c in sorted(cues, key=lambda c: c["t_in"]):
        if c.get("truth_check") != "pass":
            continue  # never voice an unverified claim (file 32)
        start, end, prio = c["t_in"], _end(c), c["priority"]
        if kept and start < kept[-1][1]:
            if prio > kept[-1][2]:
                kept[-1][1] = start
            else:
                continue
        kept.append([start, end, prio, c["cue_id"], c["text"]["radio"]])
    lines = ["WEBVTT", ""]
    for s, e, _, cid, text in kept:
        lines += [cid, f"{ts(s)} --> {ts(e)}", text, ""]
    return "\n".join(lines)
