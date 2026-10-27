"""Tier 1 item 7 (D31): spoken recaps from verified fragments, clamped to the playhead."""
from tely.qa import call_tool, load_bundle
from tely.qa.fragments import FRAGMENTS
from tely.qa.router import answer_text
from tely.qa.tools import RECAP_MAX

B = load_bundle()


def test_a_recap_never_says_what_has_not_been_revealed():
    for k in range(400):
        p = B.t0 + (B.t1 - B.t0) * k / 399
        for moment in ("so_far", "half_time", "end"):
            r = call_tool("get_recap", {"moment": moment}, playhead_s=p, bundle=B)
            assert all(B.sig(e)["reveal_t"] <= p + 1e-9 for e in r["evidence_ids"]), (p, r)
            assert len(r["evidence_ids"]) <= RECAP_MAX


def test_the_goal_joins_the_recap_only_once_var_has_let_it_stand():
    goal = next(e for e in B.events if e["type"] == "shot" and e["outcome_type"] == "successful")
    reveal = B.sig(goal["id"])["reveal_t"]
    before = call_tool("get_recap", {}, playhead_s=reveal - 0.05, bundle=B)
    after = call_tool("get_recap", {}, playhead_s=reveal + 1, bundle=B)
    assert goal["id"] not in before["evidence_ids"] and "nil, Navy nil" in before["say"]
    assert goal["id"] in after["evidence_ids"] and "Fenford scored for Navy" in after["say"]


def test_the_end_recap_is_every_big_moment_in_order_with_its_lead_and_only_known_clips():
    r = call_tool("get_recap", {"moment": "end"}, playhead_s=B.t1, bundle=B)
    assert r["fragments"][0] == "recap_end" and r["fragments"][1].startswith("score_m64_0_1")
    ts = [B.sig(e)["t"] for e in r["evidence_ids"]]
    assert ts == sorted(ts) and len(ts) == 6
    assert set(r["fragments"]) <= {f["id"] for f in FRAGMENTS}     # every piece is pre-recorded


def test_recap_by_voice_or_router():
    assert answer_text("Can you sum it up?", playhead_s=1100, bundle=B)["intent"] == "recap"
    assert answer_text("What did I miss?", playhead_s=1100, bundle=B)["intent"] == "missed"
