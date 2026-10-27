# eval/build_report.py: merges A's report.json with B's qa.json / listening.json (if present).
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def br():
    spec = importlib.util.spec_from_file_location("build_report", ROOT / "eval" / "build_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def evaldir(tmp_path):
    shutil.copyfile(ROOT / "eval" / "report.json", tmp_path / "report.json")
    return tmp_path


def test_without_b_files_it_says_not_yet(br, evaldir):
    md = br.build(evaldir)
    assert "| Spoiler leaks | 0 |" in md
    assert "Not yet: `eval/qa.json`" in md and "Not run yet: no `eval/listening.json`" in md


def test_listening_with_no_participants_shows_no_numbers(br, evaldir):
    shutil.copyfile(ROOT / "eval" / "listening.json", evaldir / "listening.json")   # the committed, empty test
    md = br.build(evaldir).split("## Eyes-closed listening test", 1)[1]
    assert "Not run yet: 0 participants" in md
    assert "Commentary only" not in md and "6.1" not in md and "|" not in md


def test_listening_results_are_rendered(br, evaldir):
    spec = importlib.util.spec_from_file_location("score_listening", ROOT / "eval" / "score_listening.py")
    sl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sl)
    rec = {"participant": "P01", "session_date": "2026-10-26", "group": "A", "sight": None, "listened_via": "in_person",
           "clips": {"commentary": {"probes": {"where": 1, "side": 0, "danger": 1, "scored": 1},
                                    "scale": {"enjoy": 2, "access": 3, "follow": 2}, "total": 7},
                     "full": {"probes": {"where": 1, "side": 1, "danger": 1, "scored": 1},
                              "scale": {"enjoy": 4, "access": 4, "follow": 4}, "total": 12}},
           "preferred": "full", "ask_tried": "yes", "ask_worked": "partly",
           "consent": {"take_part": "yes", "quote": "yes", "film": "no"}, "quote": "I knew | where it was"}
    (evaldir / "listening.json").write_text(json.dumps(sl.summarise([rec])))   # made-up test record
    md = br.build(evaldir).split("## Eyes-closed listening test", 1)[1]
    assert "**1 participant** (1 not said; listened via 1 in person)" in md and "| Commentary only | 1 | 7 (7–7) | 2 / 3 / 2 | 3/4 (75%) |" in md
    assert "| Full Tely | 1 | 12 (12–12) |" in md and "mean 5 points" in md
    assert "not evidence for blind fans" in md and "6.1/15" in md
    assert '> "I knew \\| where it was" (P01, sight not said)' in md


def test_report_json_gets_qa_and_listening(br, evaldir):
    (evaldir / "qa.json").write_text(json.dumps({"questions": 3}))
    rep = br.merged(evaldir)
    assert rep["qa"] == {"questions": 3} and rep["listening"] is None and rep["spoiler_leaks"] == 0


def test_committed_report_json_is_merged(br):
    """Rerun `python eval/build_report.py` after score_listening.py or eval_qa (it rewrites report.json too)."""
    assert json.loads((ROOT / "eval" / "report.json").read_text(encoding="utf-8")) == br.merged(ROOT / "eval")


def test_b_files_of_any_shape_are_rendered(br, evaldir):
    (evaldir / "qa.json").write_text(json.dumps({
        "questions": 22, "pass": 21, "spoiler_refusals": {"who scores next?": "refused"},
        "cases": [{"q": "where's the ball?", "ok": True}, {"q": "who wins?", "ok": True, "note": "a|b"}]}))
    (evaldir / "listening.json").write_text(json.dumps([{"tester": "T1", "felt_buildup": True}]))
    md = br.build(evaldir)
    assert "## Q&A eval (eval/qa.json)" in md and "| questions | 22 |" in md
    assert "| who scores next? | refused |" in md and "a\\|b" in md  # pipes escaped, table intact
    assert "## Listening test (eval/listening.json)" in md and "| T1 | yes |" in md


def test_committed_report_md_is_current(br):
    """eval/report.md must be regenerated whenever report.json (or B's files) change."""
    assert (ROOT / "eval" / "report.md").read_text(encoding="utf-8") == br.build(ROOT / "eval")


def test_report_md_shows_each_languages_checks(br, evaldir):
    md = br.build(evaldir)
    assert "**Commentary in other languages**" in md
    rep = json.loads((evaldir / "report.json").read_text(encoding="utf-8"))
    for lang, x in rep["languages"].items():
        assert f"| {lang} | {x['lines']} | {x['truth_check_pass']}/{x['lines']} | {x['spoiler_check_pass']}/{x['lines']} |" in md
