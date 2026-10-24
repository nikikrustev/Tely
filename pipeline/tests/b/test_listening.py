# OWNER: B lane (created by A, 24 Oct, Stage 8 item 6). eval/score_listening.py: listening_test.csv -> listening.json.
import csv
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def sl():
    spec = importlib.util.spec_from_file_location("score_listening", ROOT / "eval" / "score_listening.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write(path: Path, cols, rows) -> Path:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return path


def person(pid, group, c1, c2, **kw):
    """Test fixture only (made-up rows): c1/c2 = (4 probes, 3 ratings) for Clip 1 and Clip 2."""
    row = {"participant": pid, "session_date": "2026-10-26", "group": group, "sight": "sighted",
           "listened_via": "own_device", "headphones": "yes", "consent_take_part": "yes", "consent_quote": "no",
           "consent_film": "no", "preferred": "none", "ask_tried": "no"}
    for i, vals in ((1, c1), (2, c2)):
        for k, v in zip(("where", "side", "danger", "scored", "enjoy", "access", "follow"), vals):
            row[f"c{i}_{k}"] = v
    return {**row, **kw}


def test_committed_csv_is_empty_and_says_not_run_yet(sl):
    with (ROOT / "eval" / "listening_test.csv").open(encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f))
    assert header == sl.COLUMNS
    res = sl.score(ROOT / "eval" / "listening_test.csv")
    assert res["status"] == "not run yet" and res["participants"] == 0
    assert not {"conditions", "paired", "probes", "rows"} & res.keys()   # no numbers without people


def test_committed_listening_json_is_current(sl):
    """Rerun `python eval/score_listening.py` whenever the CSV changes."""
    committed = json.loads((ROOT / "eval" / "listening.json").read_text(encoding="utf-8"))
    assert committed == sl.score(ROOT / "eval" / "listening_test.csv")


def test_group_decides_which_clip_was_full(sl, tmp_path):
    rows = [person("P01", "A", (1, 0, 1, 1, 3, 2, 2), (1, 1, 1, 1, 5, 4, 4), preferred="2"),
            person("P02", "B", (1, 1, 1, 1, 4, 4, 5), (0, 0, 1, 1, 2, 2, 3), preferred="1", sight="blind")]
    res = sl.score(write(tmp_path / "t.csv", sl.COLUMNS, rows))
    full, com = res["conditions"]["full"], res["conditions"]["commentary"]
    assert (full["n"], full["scale_mean"], full["scale_min"], full["scale_max"]) == (2, 13.0, 13, 13)
    assert (com["scale_mean"], com["probes_right"], com["probes_asked"]) == (7.0, 5, 8)
    assert res["paired"] == {"n": 2, "mean_full_minus_commentary": 6.0, "full_higher": 2, "same": 0,
                             "commentary_higher": 0}
    assert res["preferred"]["full"] == 2 and res["probes"]["side"] == {"commentary": "0/2", "full": "2/2"}
    assert res["blind_or_partially_sighted"]["participants"] == 1
    assert res["blind_or_partially_sighted"]["full"]["scale_mean"] == 13.0


def test_consent_rules(sl, tmp_path):
    rows = [person("P01", "A", (1,) * 4 + (3,) * 3, (1,) * 4 + (4,) * 3, quote="kept", consent_quote="yes"),
            person("P02", "B", (1,) * 4 + (3,) * 3, (1,) * 4 + (4,) * 3, quote="dropped", consent_quote="no"),
            person("P03", "A", (1,) * 4 + (5,) * 3, (1,) * 4 + (5,) * 3, consent_take_part="no")]
    res = sl.score(write(tmp_path / "t.csv", sl.COLUMNS, rows))
    assert res["participants"] == 2 and res["excluded_no_consent"] == 1
    assert [q["quote"] for q in res["quotes"]] == ["kept"]
    assert "dropped" not in json.dumps(res)


def test_blank_ratings_are_left_out_not_guessed(sl, tmp_path):
    rows = [person("P01", "A", (1, "", 1, 1, 3, "", 2), (1, 1, 1, 1, 4, 4, 4))]
    res = sl.score(write(tmp_path / "t.csv", sl.COLUMNS, rows))
    assert res["conditions"]["commentary"]["n"] == 0 and res["conditions"]["commentary"]["scale_mean"] is None
    assert res["conditions"]["commentary"]["probes_asked"] == 3 and res["paired"]["n"] == 0


@pytest.mark.parametrize("bad, msg", [({"c1_enjoy": "6"}, "c1_enjoy"), ({"c2_where": "yes"}, "c2_where"),
                                      ({"group": "C"}, "group"), ({"preferred": "full"}, "preferred"),
                                      ({"participant": ""}, "participant")])
def test_bad_values_stop_with_the_row(sl, tmp_path, bad, msg):
    rows = [{**person("P01", "A", (1,) * 4 + (3,) * 3, (1,) * 4 + (3,) * 3), **bad}]
    with pytest.raises(sl.CsvError, match=rf"row 2: {msg}"):
        sl.score(write(tmp_path / "t.csv", sl.COLUMNS, rows))


def test_missing_column_and_duplicate_participant(sl, tmp_path):
    with pytest.raises(sl.CsvError, match="missing columns quote"):
        sl.score(write(tmp_path / "a.csv", [c for c in sl.COLUMNS if c != "quote"], []))
    two = [person("P01", "A", (1,) * 7, (1,) * 7)] * 2
    with pytest.raises(sl.CsvError, match="listed twice: P01"):
        sl.score(write(tmp_path / "b.csv", sl.COLUMNS, two))
