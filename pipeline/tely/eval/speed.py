"""Speed numbers judges can compare (Tier 2 item 13, D35): event -> commentary, goal -> crowd roar.

    python -m tely.eval.speed      # writes eval/speed.json (merged into eval/report.json by eval/build_report.py)

Two kinds of number, never mixed:
- scheduled, on the judge cut: when the bundle plays each sound, against the moment it belongs to. A reaction waits
  for the outcome (reveal_t: the ball reaching the keeper, crossing the line, VAR); a description follows its event.
  The crowd roar and the goal vibration are scheduled on the audio clock at the reveal itself.
- measured, in the browser: how late each commentary line was actually heard against when it was due, from the
  26 Oct soak runs (eval/soak/, both halves in real time, an analyser on every AudioContext).
Adding the two gives event -> heard. No number here is a guess: anything not measured is said to be scheduled.
"""

from __future__ import annotations

import json
import statistics
import sys
import time

from tely.commentary.source import BUNDLE, ROOT, load_match

OUT = ROOT / "eval" / "speed.json"
SOAK = sorted((ROOT / "eval" / "soak").glob("soak*_*.json"))
REACT = {"react", "call", "var", "detail", "foul"}   # lines about an outcome: timed from its reveal


def _p(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 3)


def run(cut: str = "judge") -> dict:
    m = load_match(cut)
    out_dir = BUNDLE / cut
    cues = [json.loads(s) for s in (out_dir / "cues.en.radio.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
    describe, react = [], []
    for c in cues:
        if not c["evidence"] or c["kind"] in ("build", "intro", "kits"):
            continue
        e = m.by_id(c["evidence"][0])
        if c["kind"] in REACT:
            react.append(c["t_in"] - m.reveal_t(e))
        elif c["kind"] == "describe":   # not "ball"/"state": those are the regular position updates (D15), not replies
            describe.append(c["t_in"] - m.t(e))
    lead = [m.t(m.by_id(next(i for i in c["evidence"] if m.by_id(i)["type"] == "shot"))) - c["t_in"]
            for c in cues if c["kind"] == "build"]
    segs = json.loads((out_dir / "segments.json").read_text(encoding="utf-8"))["segments"]
    goals = [e for e in m.events if e["type"] == "shot" and e["outcome_type"] == "successful"]
    roar = [o for s in segs for o in s["one_shots"] if o["kind"] == "roar"]
    buzz = [h for s in segs for h in s["haptics"] if h["tacton"] == "goal"]
    goal_roar = [min(abs(o["t"] - m.reveal_t(g)) for o in roar) for g in goals] if roar else []
    goal_buzz = [min(abs(h["t"] - m.reveal_t(g)) for h in buzz) for g in goals] if buzz else []
    soak = [json.loads(p.read_text(encoding="utf-8")) for p in SOAK]
    sync = [s["commentarySync"] for s in soak]
    return {
        "measured": time.strftime("%Y-%m-%d"), "cut": cut,
        "scheduled": {
            "reaction_after_reveal_s": {"n": len(react), "p50": _p(react, .5), "p95": _p(react, .95)},
            "description_after_event_s": {"n": len(describe), "p50": _p(describe, .5), "p95": _p(describe, .95)},
            "build_up_before_shot_s": {"n": len(lead), "p50": _p(lead, .5), "min": round(min(lead), 2) if lead else None},
            "goal_to_crowd_roar_s": {"n": len(goal_roar), "max": round(max(goal_roar), 3) if goal_roar else None},
            "goal_to_vibration_s": {"n": len(goal_buzz), "max": round(max(goal_buzz), 3) if goal_buzz else None},
        },
        "heard_in_browser": {
            "source": [p.name for p in SOAK], "lines": sum(s["cuesChecked"] for s in sync),
            "median_lag_ms": [s["medianLagMs"] for s in sync], "p90_abs_lag_ms": [s["p90AbsLagMs"] for s in sync],
            "note": "first audible output of each line against its due time, both halves of seed 24 in real time",
        },
    }


def main() -> int:
    r = run()
    OUT.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8", newline="\n")
    s = r["scheduled"]
    print(f"reaction after reveal p50 {s['reaction_after_reveal_s']['p50']} s p95 {s['reaction_after_reveal_s']['p95']} s; "
          f"description after event p50 {s['description_after_event_s']['p50']} s p95 {s['description_after_event_s']['p95']} s; "
          f"goal -> roar {s['goal_to_crowd_roar_s']['max']} s; heard lag median {r['heard_in_browser']['median_lag_ms']} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
