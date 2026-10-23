"""Run eval/qa_cases.jsonl through answer_text() and write eval/qa.json. OWNER: B (Nikolay).

    python -m audiostands.qa.eval_qa

A's eval/build_report.py merges eval/qa.json into eval/report.md (scalars first, then the rows table).

Each case states the expected behaviour (eval/qa_cases.jsonl `expect.kind`):
- answer:   the right intent, a real answer (not "didn't catch that"), every `must_include` phrase present;
- refuse:   predictions ("who scores next?") and betting are refused before any lookup;
- redirect: off-topic questions get the one-line redirect;
- clarify:  an ambiguous player ("number 9", "Gus") gets "Which player?" with at least 2 candidates.
Spoiler leak (the number that must be 0): an answer cites an event after the playhead or before its outcome is
revealed, or contains one of the case's `spoiler_words` (e.g. "Goal" while the VAR check is still running).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import answer_text
from .bundle import load_bundle

ROOT = Path(__file__).resolve().parents[3]
CASES, OUT = ROOT / "eval" / "qa_cases.jsonl", ROOT / "eval" / "qa.json"


def check(case: dict, r: dict, sig: dict) -> tuple[bool, bool, bool]:
    """(answered, correct, leak) for one case."""
    exp, p, say = case["expect"], case["playhead_s"], r.get("say", "")
    leak = any(eid in sig and (sig[eid]["t"] > p or sig[eid]["reveal_t"] > p) for eid in r.get("evidence_ids", []))
    leak = leak or any(w.lower() in say.lower() for w in exp.get("spoiler_words", []))
    kind = exp["kind"]
    if kind == "clarify":
        ok = say.startswith("Which player?") and len(r.get("candidates", [])) >= 2
        return ok, ok, leak
    if kind in ("refuse", "redirect"):
        ok = r.get("intent") == exp["intent"]
        return ok, ok, leak
    answered = r.get("intent") not in ("not_sure", "off_topic") and not say.startswith(("Sorry", "Which player?"))
    ok = answered and r.get("intent") == exp["intent"] and all(s in say for s in exp.get("must_include", []))
    return answered, ok, leak


def run(cases_path: Path = CASES) -> dict:
    b = load_bundle()
    sig = b.signals["events"]
    cases = [json.loads(s) for s in cases_path.read_text(encoding="utf-8").splitlines() if s.strip()]
    rows, by_kind = [], {}
    for c in cases:
        r = answer_text(c["question"], playhead_s=c["playhead_s"], bundle=b)
        answered, ok, leak = check(c, r, sig)
        k = c["expect"]["kind"]
        tally = by_kind.setdefault(k, [0, 0])
        tally[0] += 1
        tally[1] += ok
        rows.append({"id": c["id"], "question": c["question"], "playhead": b.clock_str(c["playhead_s"]),
                     "expected": k, "intent": r.get("intent"), "answer": r.get("say", "")[:90],
                     "answered": answered, "correct": ok, "spoiler_leak": leak})
    n = len(rows)
    return {
        "questions": n,
        "spoiler_leaks": sum(r["spoiler_leak"] for r in rows),
        "answered_pct": round(100 * sum(r["answered"] for r in rows) / n, 1),
        "correct_pct": round(100 * sum(r["correct"] for r in rows) / n, 1),
        "engine": "answer_text() keyword router, no LLM (the offline fallback)",
        "by_behaviour": {k: f"{v[1]}/{v[0]} correct" for k, v in sorted(by_kind.items())},
        "rows": rows,
    }


def write(out: Path = OUT) -> dict:
    res = run()
    out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
    return res


if __name__ == "__main__":
    r = write()
    print(f"{r['questions']} questions: {r['correct_pct']}% correct, {r['answered_pct']}% answered, "
          f"{r['spoiler_leaks']} spoiler leaks -> {OUT}")
    for row in r["rows"]:
        if not row["correct"] or row["spoiler_leak"]:
            print(f"  FAIL {row['id']}: {row['intent']} -> {row['answer']}")
