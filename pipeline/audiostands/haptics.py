"""Haptic cues {t, tacton, team} from file 41's vocabulary. OWNER: B (Nikolay).

The heartbeat itself is not listed: the browser drives it from the per-second `tension`. These are the one-off
event tactons. Outcome tactons (goal / nearMiss) fire at reveal_t, never earlier (spoiler rule).
"""
from __future__ import annotations

from .generator import FPS, PERIODS

ATTACK_AT = 0.6       # file 41: "attack building" fires once when tension crosses 0.6


def haptic_cues(events: list, rows: list, k: int, t0: float, t1: float) -> list:
    out = []
    for e in events:
        if e["period"] != PERIODS[k]:
            continue
        t, tr = e["f"] / FPS, e["reveal_f"] / FPS
        if e["type"] == "pass" and e["sub_type"] == "kick_off":
            out.append((t, "whistle1", None))
        elif e["type"] == "shot":
            out.append((t, "shot", e["team"]))
            out.append((tr, "goal" if e["outcome_type"] == "successful" else "nearMiss", e["team"]))
        elif e["type"] == "misc" and e["outcome_type"] in ("yellow_card", "red_card"):
            out.append((t, "yellow" if e["outcome_type"] == "yellow_card" else "red", e["team"]))
    for prev, row in zip(rows, rows[1:]):
        if prev["tension"] < ATTACK_AT <= row["tension"]:
            out.append((float(row["t"]), "attack", row["poss"]))
    out = [dict(t=round(t, 2), tacton=tac, team=team) for t, tac, team in out if t0 <= t <= t1]
    out.sort(key=lambda c: (c["t"], c["tacton"]))
    return out
