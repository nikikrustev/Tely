"""Spoiler-leak eval (file 43) and "spoiler lift" (file 39). CI target: spoiler_leaks() == []. OWNER: A (potencialbg).

    python -m tely.spoiler --cut judge      # report on the built cues; exit 1 on any leak
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

D_S = 10.0  # look-ahead window / broadcast delay (file 39, file 43 §2)
# File 43's outcome words, plus the ones our templates use for saves and misses.
OUTCOME = {"goal", "scores", "scored", "saved", "save", "wide", "miss", "missed", "blocked", "post",
           "saves", "denied", "woodwork", "finishes", "nets"}
# A pass's outcome (ours): checked only while that pass is in the air, because "cut out" about an earlier
# interception is normal commentary.
PASS_OUTCOME = {"cut", "intercepted", "intercepts"}
_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")


def words(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def flat_events(match) -> list[dict]:
    """CDF events plus t / reveal_t from signals, in the flat shape the file 43 code expects."""
    return [{"id": e["id"], "type": e["type"], "outcome_type": e["outcome_type"], "t": match.t(e),
             "reveal_t": match.reveal_t(e), "xg": match.sig(e["id"])["xg"]} for e in match.events]


def spoiler_leaks(cues: list[dict], events: list[dict]) -> list[tuple[str, str]]:
    """(cue_id, event_id) for every line that uses an outcome word while a shot's outcome is still unknown.

    File 43 checks lines that start within D before the shot. We also check from the shot until its reveal_t
    (when the ball reaches the keeper or crosses the line), because the outcome is unknown until then too.
    """
    hits = []
    for c in cues:
        said = words(c["text"]["radio"])
        for e in events:
            unknown_until = max(e["t"], e.get("reveal_t", e["t"]))
            if e["type"] == "shot" and said & OUTCOME and e["t"] - D_S < c["t_in"] < unknown_until:
                hits.append((c["cue_id"], e["id"]))
            elif e["type"] == "pass" and said & PASS_OUTCOME and e["t"] <= c["t_in"] < unknown_until:
                hits.append((c["cue_id"], e["id"]))
    return hits


def spoiler_lift(cues: list[dict], events: list[dict]) -> dict:
    """P(goal | a build-up fired) against the mean xG of those chances. Equal means the build-up gives nothing away."""
    built = {c["evidence"][0] for c in cues if c["kind"] == "build"}
    shots = [e for e in events if e["type"] == "shot" and e["id"] in built]
    n = len(shots)
    if not n:
        return {"n": 0, "p_goal_given_build": None, "mean_xg": None, "lift": None}
    p = sum(e["outcome_type"] == "successful" for e in shots) / n
    xg = sum(e["xg"] or 0 for e in shots) / n
    return {"n": n, "p_goal_given_build": round(p, 3), "mean_xg": round(xg, 3), "lift": round(p - xg, 3),
            "note": "n is far too small to judge; the number becomes meaningful over many seeds" if n < 30 else ""}


def report(cues: list[dict], events: list[dict]) -> dict:
    return {"spoiler_leaks": spoiler_leaks(cues, events), "spoiler_lift": spoiler_lift(cues, events),
            "lines": len(cues)}


def main(argv: list[str] | None = None) -> int:
    from tely.commentary.source import BUNDLE, load_match

    ap = argparse.ArgumentParser(description="Spoiler-leak and spoiler-lift report for a built cue file")
    ap.add_argument("--cut", default="judge")
    ap.add_argument("--cues", type=Path, help="default: web/public/replay/v1/<cut>/cues.en.radio.jsonl")
    args = ap.parse_args(argv)
    path = args.cues or BUNDLE / args.cut / "cues.en.radio.jsonl"
    cues = [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]
    rep = report(cues, flat_events(load_match(args.cut)))
    print(json.dumps(rep, indent=1))
    return 1 if rep["spoiler_leaks"] else 0


if __name__ == "__main__":
    sys.exit(main())
