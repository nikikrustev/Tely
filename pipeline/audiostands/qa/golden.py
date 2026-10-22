"""Write contracts/golden/b/qa_cases.jsonl: the offline tools' exact answers at many playheads. OWNER: B (Nikolay).

    python -m audiostands.qa.golden

Both pytest (pipeline/tests/b/test_qa_golden.py) and vitest (web/tests/b/ask.test.ts) replay every case, so the Python
tools and their TypeScript copies in web/src/ask/local-tools.ts always say the same thing (TEAM_SPLIT.md seam 4).
Cases cover the tools the browser runs offline: score, ball, last events, what did I miss, catch-up, hold that thought.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import hold_that_thought
from .bundle import Bundle, load_bundle
from .tools import call, catch_up_answer

OUT = Path(__file__).resolve().parents[3] / "contracts" / "golden" / "b" / "qa_cases.jsonl"


def playheads(b: Bundle) -> list[float]:
    ps = {round(b.t0 + k * 15.0, 2) for k in range(int((b.t1 - b.t0) // 15) + 1)}
    for e in b.events:                                  # the edges where spoilers would hide
        s = b.sig(e["id"])
        if s["priority"] >= 2:
            for t in (s["t"] - 0.1, s["t"], s["reveal_t"] - 0.04, s["reveal_t"], s["reveal_t"] + 1.0):
                if b.t0 <= t <= b.t1:
                    ps.add(round(t, 2))
    return sorted(ps)


def cases(b: Bundle) -> list[dict]:
    out = []
    for p in playheads(b):
        for tool, args in (("get_score_and_clock", {}), ("get_ball_position", {}), ("get_last_events", {"n": 2}),
                           ("what_did_i_miss", {"since": b.clock_str(max(b.t0, p - 60))})):
            r = call(tool, args, p, b)
            out.append({"tool": tool, "args": args, "playhead_s": p, "expected_say": r["say"],
                        "expected_fragments": r["fragments"], "expected_evidence": r["evidence_ids"]})
        r = catch_up_answer(b, max(b.t0, p - 30), p)
        out.append({"tool": "catch_up", "args": {"since_s": round(max(b.t0, p - 30), 2)}, "playhead_s": p,
                    "expected_say": r["say"], "expected_fragments": r["fragments"], "expected_evidence": r["evidence_ids"]})
        out.append({"tool": "hold_that_thought", "args": {}, "playhead_s": p, "expected": hold_that_thought(p, b)})
    return out


def write(path: Path = OUT, b: Bundle | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = cases(b or load_bundle())
    path.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows), encoding="utf-8", newline="\n")
    return path


if __name__ == "__main__":
    p = write()
    print(f"wrote {p} ({sum(1 for _ in p.open(encoding='utf-8'))} cases)")
