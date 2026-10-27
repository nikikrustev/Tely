# The Q&A eval (eval/qa_cases.jsonl -> eval/qa.json): enough questions of every required kind,
# zero spoiler leaks, every expected behaviour met, and the committed eval/qa.json matches a fresh run.
from __future__ import annotations

import json

import pytest

from tely.qa import eval_qa

CASES = [json.loads(s) for s in eval_qa.CASES.read_text(encoding="utf-8").splitlines() if s.strip()]


def test_the_question_set_covers_what_the_plan_asks_for():
    qs = {c["question"].lower() for c in CASES}
    kinds = [c["expect"]["kind"] for c in CASES]
    assert len(CASES) >= 20
    assert "who scores next?" in qs and "who wins?" in qs                      # the two spoiler questions
    assert kinds.count("redirect") >= 2 and kinds.count("clarify") >= 3 and kinds.count("refuse") >= 4
    assert len({c["id"] for c in CASES}) == len(CASES)


def test_zero_spoiler_leaks_and_every_behaviour_met():
    r = eval_qa.run()
    assert r["spoiler_leaks"] == 0
    bad = [row for row in r["rows"] if not row["correct"]]
    assert not bad, bad


def test_qa_json_is_current_when_present():
    # eval/qa.json lands together with A's regenerated eval/report.md (A's test checks report.md against it), so it
    # may be absent here; when it is present it must match a fresh run.
    if not eval_qa.OUT.exists():
        pytest.skip("eval/qa.json not committed yet (A commits it with eval/report.md)")
    assert json.loads(eval_qa.OUT.read_text(encoding="utf-8")) == eval_qa.run(), "rerun: python -m tely.qa.eval_qa"
