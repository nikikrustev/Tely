"""Find the judge cut: the first seed (1-500) with an 8-minute window inside one half that has >= 1 goal,
>= 1 save, >= 1 card, a VAR-style check and >= 4 shots ().

    python -m tely.judge_cut          # writes pipeline/judge_cut.json

Two extra conditions (ours): the score is 0-0 when the window opens, because A's loader counts goals from the
window's own events; and every outcome inside the window is also revealed inside it.
"""
from __future__ import annotations

import json
from pathlib import Path

from .generator import FPS, PERIODS, generate

WINDOW_S = 480
STEP_S = 10
OUT = Path(__file__).resolve().parents[1] / "judge_cut.json"


def window_ok(events: list, k: int, t0: int, t1: int, goals_before: int) -> bool:
    if goals_before:
        return False
    f0, f1 = t0 * FPS, t1 * FPS
    inside = [e for e in events if e["period"] == PERIODS[k] and f0 <= e["f"] <= f1]
    if any(e["reveal_f"] > f1 for e in inside):
        return False
    shots = [e for e in inside if e["type"] == "shot"]
    return (len(shots) >= 4
            and any(e["outcome_type"] == "successful" for e in shots)
            and any(e["type"] == "goalkeeping" and e["sub_type"] == "save" for e in inside)
            and any(e.get("outcome_type") in ("yellow_card", "red_card") for e in inside)
            and any(e["type"] == "referee" and e["sub_type"] == "var_check" for e in inside))


def find(seeds=range(1, 501)) -> dict:
    for seed in seeds:
        m = generate(seed)
        for k, per in enumerate(m["periods"]):
            last = per["end_f"] // FPS - WINDOW_S
            for t0 in range(0, last + 1, STEP_S):
                f0 = t0 * FPS
                before = sum(1 for e in m["events"] if e["type"] == "shot" and e["outcome_type"] == "successful"
                             and (PERIODS.index(e["period"]), e["reveal_f"]) < (k, f0))
                if window_ok(m["events"], k, t0, t0 + WINDOW_S, before):
                    return dict(seed=seed, period=PERIODS[k], t_start=t0, t_end=t0 + WINDOW_S)
    raise SystemExit("no seed in range has a qualifying window: retune generator.py")


if __name__ == "__main__":
    cut = find()
    OUT.write_text(json.dumps(cut, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(cut)
