# OWNER: A (potencialbg). eval/build_report.py: merges A's report.json with B's qa.json / listening.json (if present).
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


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
    assert "Not yet: `eval/qa.json`" in md and "Not yet: `eval/listening.json`" in md


def test_b_files_of_any_shape_are_rendered(br, evaldir):
    (evaldir / "qa.json").write_text(json.dumps({
        "questions": 22, "pass": 21, "spoiler_refusals": {"who scores next?": "refused"},
        "cases": [{"q": "where's the ball?", "ok": True}, {"q": "who wins?", "ok": True, "note": "a|b"}]}))
    (evaldir / "listening.json").write_text(json.dumps([{"tester": "T1", "felt_buildup": True}]))
    md = br.build(evaldir)
    assert "## Q&A eval (Person B, eval/qa.json)" in md and "| questions | 22 |" in md
    assert "| who scores next? | refused |" in md and "a\\|b" in md  # pipes escaped, table intact
    assert "## Listening test (Person B, eval/listening.json)" in md and "| T1 | yes |" in md


def test_committed_report_md_is_current(br):
    """eval/report.md must be regenerated whenever report.json (or B's files) change."""
    assert (ROOT / "eval" / "report.md").read_text(encoding="utf-8") == br.build(ROOT / "eval")
