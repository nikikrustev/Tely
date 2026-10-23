# OWNER: B (Nikolay). Written FIRST (B5 prompt): the pitch says "0 spoiler leaks", so this is the test that matters most.
# Across 200 random playheads, no tool answer, router answer or catch-up uses evidence from after the playhead:
# every evidence event happened at or before it AND its outcome was already revealed (signals reveal_t).
from __future__ import annotations

import random

import pytest

from audiostands import qa
from audiostands.qa.bundle import load_bundle

B = load_bundle()
SIG = B.signals["events"]
PLAYERS = [p for side in ("home", "away") for p in B.meta["teams"][side]["players"]]
QUESTIONS = ["what's the score", "where's the ball", "what just happened", "what did I miss",
             "who will win", "who scores next", "how is the weather", "where is number 9"]


def playheads(n=200, seed=1234):
    rng = random.Random(seed)
    return [round(rng.uniform(B.t0, B.t1), 2) for _ in range(n)]


def assert_no_future(res: dict, p: float, what: str) -> None:
    for eid in res.get("evidence_ids", []):
        if eid in SIG:                                   # event ids; track/score ids are checked by as_of_clock
            assert SIG[eid]["t"] <= p + 1e-6, f"{what}: {eid} happens after the playhead {p}"
            assert SIG[eid]["reveal_t"] <= p + 1e-6, f"{what}: {eid}'s outcome is revealed after the playhead {p}"
    if "as_of_clock" in res:
        assert res["as_of_clock"] == B.clock_str(p), what


@pytest.mark.parametrize("p", playheads())
def test_no_tool_answer_uses_the_future(p):
    rng = random.Random(int(p * 100))
    player = rng.choice(PLAYERS)
    recent = [eid for eid, s in SIG.items() if s["reveal_t"] <= p]
    calls = [
        ("get_score_and_clock", {}),
        ("get_ball_position", {}),
        ("where_is", {"player": player["last_name"]}),
        ("get_player_stats", {"player": str(player["jersey_number"]) if rng.random() < 0.5 else player["name"]}),
        ("get_last_events", {"n": rng.randint(1, 5)}),
        ("explain_moment", {"moment_id": rng.choice(list(SIG))}),
        ("what_did_i_miss", {"since": B.clock_str(max(B.t0, p - rng.uniform(5, 120)))}),
        ("set_preferences", {"verbosity": "calm"}),
    ]
    if recent:
        calls.append(("explain_moment", {"moment_id": rng.choice(recent)}))
    for name, args in calls:
        res = qa.call_tool(name, args, playhead_s=p, bundle=B)
        assert ("say" in res) != ("error" in res), (name, res)
        assert_no_future(res, p, name)
    for q in QUESTIONS:
        assert_no_future(qa.answer_text(q, playhead_s=p, bundle=B), p, q)


@pytest.mark.parametrize("p", playheads(60, seed=99))
def test_catch_up_mentions_only_what_was_revealed_in_the_window(p):
    since = max(B.t0, p - 90)
    text = qa.catch_up(since, p, B)
    for eid, s in SIG.items():
        past = s["spoken_past"]
        if past in text:
            assert since < s["reveal_t"] <= p and s["t"] <= p, (eid, past)


def test_hold_that_thought_says_that_never_what():
    assert all(isinstance(qa.hold_that_thought(p, B), bool) for p in playheads(200, seed=7))


def test_catch_up_during_the_var_check_includes_the_confirmed_goal():
    # Martin's review: the goal is struck before the Ask (t 679.4) and confirmed during it (reveal 703.76).
    goal = next(e for e in B.events if e["type"] == "shot" and e["outcome_type"] == "successful")
    assert SIG[goal["id"]]["t"] < 690 < SIG[goal["id"]]["reveal_t"] <= 730
    assert SIG[goal["id"]]["spoken_past"] in qa.catch_up(690, 730, B)
    assert qa.catch_up(690, 700, B) == "Back to the action."   # not yet confirmed at 700
