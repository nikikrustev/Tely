# OWNER: A (potencialbg). Stage 5 eval (audiostands.eval). No Azure: replayed Director, fake synthesiser.
import asyncio
import json
import re

import pytest

from audiostands.agents import director as D
from audiostands.build_bundle import recorded
from audiostands.commentary import planner
from audiostands.commentary.source import load_match
from audiostands.commentary.tts import load_env
from audiostands.eval import metrics, numeric_truth, realtime


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
