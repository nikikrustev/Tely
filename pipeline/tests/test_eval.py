# Stage 5 eval (tely.eval). No Azure: replayed Director, fake synthesiser.
import asyncio
import json
import re

import pytest

from tely.agents import director as D
from tely.build_bundle import recorded
from tely.commentary import planner
from tely.commentary.source import load_match
from tely.commentary.tts import load_env
from tely.eval import metrics, numeric_truth, realtime


class FakeSynth:
    def synthesise(self, doc):
        text = re.sub(r"<[^>]+>|\[\w+\]", "", doc)
        return b"ID3fake", planner.estimate(text, "", 0)


@pytest.fixture(scope="module")
def judge():
    return load_match("judge")


def test_grade_is_file_18s_grader():
    item = {"claims": [{"metric": "score", "subject": "home", "value": 1},
                       {"metric": "minute", "subject": "clock", "value": 56}],
            "truth": {"score:home": 1, "minute:clock": 57}}
    assert numeric_truth.grade({}, item) == 0.5
    assert numeric_truth.grade({}, {"claims": [], "truth": {}}) == 1.0


def test_claims_parse_scores_and_clock(judge):
    home, away = judge.team_name("home"), judge.team_name("away")
    got = numeric_truth.claims(judge, f"{home} nil, {away} one, fifty-six minutes played.")
    assert got == [{"metric": "score", "subject": "home", "value": 0}, {"metric": "score", "subject": "away", "value": 1},
                   {"metric": "minute", "subject": "clock", "value": 56}]


def test_report_on_the_committed_bundle(judge):
    # CI has no .env: the voice the bundle was built with is in its manifest
    voice = load_env().get("TTS_VOICE") or json.loads(
        (metrics.BUNDLE / "judge" / "manifest.json").read_text(encoding="utf-8"))["voice"]
    rep = metrics.report(judge, "judge", voice, recorded("judge"))
    assert rep["spoiler_leaks"] == 0 and rep["truth_check_pass"] == rep["lines"]
    assert rep["numbers"]["pct_verified"] == 100.0
    assert rep["director"]["calls"] >= 1 and rep["director"]["fallbacks"] == 0
    assert rep["templates"]["llm_lines"] == 0


def test_realtime_harness_times_every_build_line(judge):
    calls = []

    async def no_wait(s):
        calls.append(s)

    rows = asyncio.run(realtime.one_run(judge, D.ReplayDirector(recorded("judge")), FakeSynth(),
                                        "en-US-Brian:DragonHDLatestNeural", speed=1.0, run_no=1, sleep=no_wait))
    assert len(rows) == 4 and calls  # it waited for each shot (patched to return at once)
    for r in rows:
        assert r["total_ms"] >= r["plan_ms"] and r["within_budget"]  # fakes are instant
    rep = realtime.summarise(rows, 1.0, 1)
    assert rep["build_lines"] == sum(r["build"] for r in rows) >= 1
    assert rep["budget_ms"] == [6000]  # recorded plans use lead_s 4.0 on build-ups: 10 - 4 = 6 s (file 43 §2)


def test_percentiles():
    assert realtime.pct([], 50) is None
    assert realtime.pct([1, 2, 3, 4], 50) == 2 and realtime.pct([1, 2, 3, 4], 95) == 4
    # Nearest rank is the ceil(q/100 * n)-th value. round(x + 0.5) rounded halves to even and took one too many:
    assert realtime.pct([1, 2], 50) == 1                     # was 2
    assert realtime.pct(list(range(1, 11)), 50) == 5         # was 6
    assert realtime.pct(list(range(1, 7)), 50) == 3          # was 4
    assert realtime.pct(list(range(1, 21)), 95) == 19 and realtime.pct(list(range(1, 11)), 95) == 10
    assert realtime.pct([5], 50) == 5 and realtime.pct([1, 2, 3], 0) == 1


def test_stored_realtime_runs_are_resummarised_from_their_rows():
    rows = [{"build": True, "budget_ms": 6000, "within_budget": True, "fallback": None, "plan_ms": p, "verify_ms": 1.0,
             "tts_ms": 1.0, "total_ms": p + 2} for p in (100.0, 300.0)]
    old = {"measured": "2026-10-23 01:06", "director": "d", "traces": "t", "speed": 1.0, "runs": 1, "rows": rows,
           "p50_ms": {"total_ms": 302.0}}
    new = realtime.resummarise(old)
    assert new["p50_ms"]["total_ms"] == 102.0 and new["p95_ms"]["total_ms"] == 302.0
    assert (new["measured"], new["director"], new["traces"], new["rows"]) == (old["measured"], "d", "t", rows)
    assert realtime.resummarise({"speed": 1.0}) == {"speed": 1.0}


def test_report_counts_each_languages_truth_and_spoiler_checks(judge, tmp_path):
    rep = metrics.languages(judge, "judge")
    from tely.commentary.languages import LANGS
    assert set(rep) == set(LANGS)
    for lang, x in rep.items():
        assert x["aligned"] and x["lines"] == 70, lang
        assert x["truth_check_pass"] == x["spoiler_check_pass"] == x["lines"], (lang, x)
    # a wrong minute in a copy of the German track is counted, not hidden
    import shutil
    d = tmp_path / "judge"
    d.mkdir()
    for name in ("cues.en.radio.jsonl", "cues.de.radio.jsonl"):
        shutil.copyfile(metrics.BUNDLE / "judge" / name, d / name)
    de = (d / "cues.de.radio.jsonl").read_text(encoding="utf-8").replace("sechsundfünfzig", "fünfundfünfzig")
    (d / "cues.de.radio.jsonl").write_text(de, encoding="utf-8", newline="\n")
    bad = metrics.languages(judge, "judge", tmp_path)
    assert list(bad) == ["de"] and bad["de"]["truth_check_pass"] == 69
