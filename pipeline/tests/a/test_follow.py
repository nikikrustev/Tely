"""D34: follow my player. The commentator can start and stop it by voice; the names are roster-only fragments."""
from tely.qa import call_tool, load_bundle
from tely.qa.fragments import FRAGMENTS

B = load_bundle()
P = (B.t0 + B.t1) / 2


def test_follow_by_name_or_number_and_stop():
    r = call_tool("set_preferences", {"follow": "Olvholm"}, playhead_s=P, bundle=B)
    pid = r["prefs"]["follow"]
    assert B.players[pid]["last_name"] == "Olvholm" and "Following" in r["say"]
    assert call_tool("set_preferences", {"follow": "nobody"}, playhead_s=P, bundle=B)["prefs"] == {"follow": None}
    assert "candidates" in call_tool("set_preferences", {"follow": "the keeper"}, playhead_s=P, bundle=B)


def test_every_player_has_a_name_clip_and_it_says_nothing_but_the_name():
    names = {f["id"]: f["text"] for f in FRAGMENTS if f["id"].startswith("name_")}
    assert len(names) == len(B.players) == 22
    for pid, p in B.players.items():
        assert names[f"name_{pid}"] == f"{p['last_name']} on the ball."
