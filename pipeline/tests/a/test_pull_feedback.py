# OWNER: A (potencialbg). eval/pull_feedback.py (D19): tester-mode events -> raw CSV + self-run listening rows.
# No az, no Azure: events are made up here in the shape the relay logs (customDimensions are strings).
import base64
import csv
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "eval" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pf():
    return load("pull_feedback")


def ev(tester, eid, kind, ts="2026-10-25T10:00:00Z", **kw):
    base = {"timestamp": ts, "v": "1", "kind": kind, "tester": tester, "eid": eid, "group": "B",
            "consent_take_part": "true", "consent_quote": "false"}
    return {**base, **{k: str(v) for k, v in kw.items()}}


def clip(tester, eid, n, ok=1, scale=4):
    return ev(tester, eid, "clip", clip=n, where="left_close", where_ok=ok, side_ok=ok, danger_ok=ok, scored_ok=0,
              enjoy=scale, access=scale, follow=scale)


def finished(tester="t-0000000b"):
    return [ev(tester, "00000001", "consent"), clip(tester, "00000002", 1, ok=1, scale=5), clip(tester, "00000003", 2, ok=0, scale=2),
            ev(tester, "00000004", "ask", ask_presets=2, ask_live_available="true", ask_live_tried="false", ask_worked="yes"),
            ev(tester, "00000005", "overall", liked="Хареса ми", preferred="1", device="iphone", headphones="bluetooth",
               screen_reader="voiceover", sight="not_said")]


def test_a_tester_who_finished_both_clips_becomes_one_self_run_row(pf):
    t = pf.per_tester(finished())
    row = pf.listening_row("t-0000000b", t["t-0000000b"])
    assert row["mode"] == "self" and row["group"] == "B" and row["session_date"] == "2026-10-25"
    assert row["sight"] == "sighted, eyes closed"            # "rather not say" -> the self-run default
    assert (row["c1_where"], row["c1_scored"], row["c1_enjoy"], row["c2_where"], row["c2_follow"]) == ("1", "0", "5", "0", "2")
    assert (row["ask_tried"], row["ask_worked"], row["headphones"], row["screen_reader"]) == ("yes", "yes", "yes", "VoiceOver")
    assert (row["consent_take_part"], row["consent_quote"], row["consent_film"]) == ("yes", "no", "no")
    assert row["quote"] == "" and row["notes"] == "" and "Хареса" not in json.dumps(row)   # free text stays out of the repo


def test_unfinished_or_no_consent_is_not_a_row(pf):
    one_clip = [e for e in finished() if not (e["kind"] == "clip" and e["clip"] == "2")]
    assert pf.listening_row("t-0000000b", pf.per_tester(one_clip)["t-0000000b"]) is None
    no = [{**e, "consent_take_part": "false"} for e in finished()]
    assert pf.listening_row("t-0000000b", pf.per_tester(no)["t-0000000b"]) is None


def test_told_us_their_sight(pf):
    evs = finished()
    evs[-1] = {**evs[-1], "sight": "blind"}
    assert pf.listening_row("t-0000000b", pf.per_tester(evs)["t-0000000b"])["sight"] == "blind"


def test_retries_and_pasted_copies_count_once(pf):
    evs = finished() + finished()[1:3]
    text = "Code for the team:\nAS1." + base64.b64encode(json.dumps(
        [{"v": 1, "kind": "task", "tester": "t-0000000b", "eid": "00000009", "group": "B", "task": 2, "result": "done",
          "consent_take_part": True}]).encode()).decode()
    pasted = pf.from_paste(text)
    assert pasted[0]["consent_take_part"] == "true" and pasted[0]["task"] == "2"
    assert len(pf.dedupe(evs + pasted)) == len(finished()) + 1


def test_append_is_idempotent_and_scored_apart(pf, tmp_path):
    sl = load("score_listening")
    csv_path = tmp_path / "listening_test.csv"
    shutil.copyfile(ROOT / "eval" / "listening_test.csv", csv_path)
    testers = pf.per_tester(finished("t-0000000b") + finished("t-0000000a"))
    assert pf.append_listening(testers, csv_path) == ["t-0000000a", "t-0000000b"]
    assert pf.append_listening(testers, csv_path) == []      # never twice
    with csv_path.open(encoding="utf-8", newline="") as f:
        assert [r["mode"] for r in csv.DictReader(f)] == ["self", "self"]
    res = sl.score(csv_path)
    assert res["status"] == "not run yet" and res["participants"] == 0      # moderated numbers untouched
    sr = res["self_run"]
    assert sr["participants"] == 2 and sr["sight"]["sighted, eyes closed"] == 2
    assert "not blind or partially sighted fans" in sr["note"]


def test_raw_csv_has_every_schema_column(pf, tmp_path):
    out = tmp_path / "feedback.csv"
    pf.write_raw(finished(), out)
    with out.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0].keys() == {"timestamp", *pf.SCHEMA}
    assert rows[-1]["liked"] == "Хареса ми"


def test_raw_feedback_is_git_ignored():
    assert "out/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_report_says_self_run_volunteers_are_not_blind_fans(pf, tmp_path):
    sl, br = load("score_listening"), load("build_report")
    csv_path = tmp_path / "listening_test.csv"
    shutil.copyfile(ROOT / "eval" / "listening_test.csv", csv_path)
    pf.append_listening(pf.per_tester(finished("t-0000000b") + finished("t-0000000a")), csv_path)
    md = "\n".join(br.listening_section(sl.score(csv_path)))
    assert "Moderated sessions: not run yet" in md
    assert "### Self-run, sighted volunteers" in md and "not evidence for blind fans" in md
    assert "**2 participants** (2 sighted, eyes closed;" in md
