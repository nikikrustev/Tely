# OWNER: B (Nikolay). The Python tools reproduce every golden case (contracts/golden/b/qa_cases.jsonl). vitest replays
# the same file against web/src/ask/local-tools.ts, so both languages always say the same thing (TEAM_SPLIT seam 4).
from __future__ import annotations

import json

from tely.qa import golden, hold_that_thought
from tely.qa.bundle import load_bundle
from tely.qa.tools import call, catch_up_answer

B = load_bundle()
CASES = [json.loads(s) for s in golden.OUT.read_text(encoding="utf-8").splitlines()]


def test_golden_file_is_current(tmp_path):
    fresh = golden.write(tmp_path / "qa_cases.jsonl", B)
    assert fresh.read_bytes() == golden.OUT.read_bytes(), "rerun: python -m tely.qa.golden"


def test_python_tools_reproduce_every_case():
    assert len(CASES) > 200
    for c in CASES:
        p = c["playhead_s"]
        if c["tool"] == "hold_that_thought":
            assert hold_that_thought(p, B) == c["expected"], c
            continue
        r = catch_up_answer(B, c["args"]["since_s"], p) if c["tool"] == "catch_up" else call(c["tool"], c["args"], p, B)
        assert (r["say"], r["fragments"], r["evidence_ids"]) == (c["expected_say"], c["expected_fragments"],
                                                                 c["expected_evidence"]), c


def test_every_offline_fragment_exists():
    from tely.qa import FRAGMENTS
    ids = {f["id"] for f in FRAGMENTS}
    used = {f for c in CASES for f in (c.get("expected_fragments") or [])}
    assert used <= ids, used - ids
