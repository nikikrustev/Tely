"""adjust_sound: the fan changes one sound out loud, on the 0..100 scale the page's mixer shows (web/src/audio/mix.ts)."""
from tely import qa
from tely.qa.bundle import load_bundle
from tely.qa.tools import SOUNDS

B = load_bundle()
P = (B.t0 + B.t1) / 2


def call(**args):
    return qa.call_tool("adjust_sound", args, playhead_s=P, bundle=B)


def test_the_schema_names_every_sound_the_tool_knows():
    schema = next(t for t in qa.TOOL_SCHEMAS if t["name"] == "adjust_sound")["parameters"]["properties"]
    assert schema["sound"]["enum"] == list(SOUNDS)
    assert "current" not in schema and "playhead_s" not in schema   # the relay adds the level, never the model


def test_down_by_five_from_the_pages_level():
    r = call(sound="whistle", change=-5, current=30)
    assert r["prefs"] == {"sound": "whistle", "level": 25}
    assert r["say"] == "The whistle is now 25 out of 100."


def test_a_level_is_set_and_clamped():
    assert call(sound="chants", level=40)["prefs"] == {"sound": "chants", "level": 40}
    assert call(sound="chants", level=140)["prefs"]["level"] == 100
    off = call(sound="net", level=0)
    assert off["prefs"]["level"] == 0 and off["say"] == "The ball in the net is now off."


def test_at_the_edge_it_says_so():
    r = call(sound="crowd", change=-10, current=0)
    assert r["prefs"]["level"] == 0 and "already at 0" in r["say"]


def test_without_the_pages_level_it_sends_the_change():
    r = call(sound="reactions", change=10)
    assert r["prefs"] == {"sound": "reactions", "change": 10}
    assert r["say"] == "The crowd reactions, up by 10."


def test_unknown_sound_or_no_amount_is_an_error_with_choices():
    assert call(sound="music", change=5)["candidates"] == list(SOUNDS)
    assert call(sound="whistle")["error"] == "bad_arguments"
    assert call()["error"] == "unknown_sound"


def test_it_never_touches_the_match():
    before = qa.call_tool("get_score_and_clock", {}, playhead_s=P, bundle=B)
    call(sound="commentator", change=-5, current=50)
    assert qa.call_tool("get_score_and_clock", {}, playhead_s=P, bundle=B) == before
