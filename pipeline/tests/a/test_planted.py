"""D32: planted errors. The checks must catch every planted error and block no clean line, at the thresholds set
before the first run; eval/planted.json must be what the code gives today."""
import json

from tely.eval import planted as P


def test_thresholds_are_the_ones_set_before_the_first_run():
    assert P.THRESHOLDS == {"commentary_catch_rate_min": 1.0, "commentary_false_block_max": 0.0,
                            "answers_catch_rate_min": 0.99, "answers_false_block_max": 0.0,
                            "verifier_off_caught_max": 0.0, "director_input_identical_min": 1.0,
                            "director_outcome_reply_blocked_min": 1.0}


def test_planted_errors_are_caught_and_clean_lines_pass():
    r = P.run()
    assert r["verdict"]["pass"], r["verdict"]["checks"]
    assert r["commentary"]["planted"] > 100 and r["answers"]["planted"] > 900
    assert set(r["commentary"]["by_kind"]) == {"name", "score", "minute", "invented_number", "spoiler"}


def test_committed_planted_json_is_current():
    old = json.loads(P.OUT.read_text(encoding="utf-8"))
    new = P.run()
    for k in ("commentary", "answers", "verifier_off", "director", "verdict"):
        assert old[k] == new[k], f"rerun: python -m tely.eval.planted ({k})"
