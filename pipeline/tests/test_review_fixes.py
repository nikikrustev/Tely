"""Regression tests for the independent review of a55ab1a (items 9-13): the score at a goal's reveal, the spoken
numbers in every language, bad playheads and arguments, the ball while a shot is unrevealed, and the wider outcome
word lists."""
import json
import math

import pytest

from tely.commentary import languages as L
from tely.commentary.numbers import mismatch, numbers
from tely.commentary.source import BUNDLE, load_match
from tely.qa import call_tool, load_bundle
from tely.qa.fragments import FRAGMENTS
from tely.qa.tools import call

B = load_bundle()
GOAL = next(e for e in B.events if e["type"] == "shot" and e["outcome_type"] == "successful")
REVEAL = B.sig(GOAL["id"])["reveal_t"]
FRAGMENT_IDS = {f["id"] for f in FRAGMENTS}


# ---- 9. the score counts a goal from its reveal, not from the next whole second ---------------------------------
def test_the_score_counts_a_goal_from_its_reveal_like_the_commentary_verifier():
    m = load_match("judge")
    assert REVEAL != math.floor(REVEAL)                  # 703.76: the bug lived in (703.76, 704)
    for p in (REVEAL - 0.01, REVEAL, REVEAL + 0.1, B.t1):
        assert B.score(p) == m.score_at(p), p
    assert B.score(REVEAL + 0.1) == {"home": 0, "away": 1}


def test_explain_moment_on_the_goal_says_the_score_it_made():
    r = call("explain_moment", {"moment_id": GOAL["id"]}, REVEAL, B)
    assert r["say"].endswith("That made it Reds 0, Navy 1."), r


def test_recap_and_score_just_after_the_reveal_say_the_goal_and_the_score_together():
    rec = call("get_recap", {}, REVEAL + 0.1, B)
    assert GOAL["id"] in rec["evidence_ids"] and "Reds nil, Navy one" in rec["say"], rec
    sc = call("get_score_and_clock", {}, REVEAL + 0.1, B)
    assert sc["say"].startswith("Reds nil, Navy one") and sc["evidence_ids"] == [GOAL["id"]]
    assert set(sc["fragments"]) <= FRAGMENT_IDS and set(rec["fragments"]) <= FRAGMENT_IDS   # the offline clip exists
    before = call("get_score_and_clock", {}, REVEAL - 0.01, B)
    assert before["say"].startswith("Reds nil, Navy nil") and before["evidence_ids"] == []


# ---- 10. every translation says exactly the English line's numbers ------------------------------------------------
def test_numbers_are_read_in_digits_and_in_words_in_every_language():
    assert numbers("en", "Reds nil, Navy one, fifty-six minutes played.")[0] == {0: 1, 1: 1, 56: 1}
    assert numbers("de", "die Blauen eins, sechsundfünfzig Minuten")[0] == {1: 1, 56: 1}
    assert numbers("es", "los Azules uno, cincuenta y seis minutos")[0] == {1: 1, 56: 1}
    assert numbers("fr", "cinquante-six minutes, soixante et onze, quatre-vingt-dix")[0] == {56: 1, 71: 1, 90: 1}
    assert numbers("bg", "Червените нула, петдесет и шест, 56-та минута")[0] == {0: 1, 56: 2}
    assert numbers("ar", "الحمر صفر، الزرق واحد، دقيقة ست وخمسون، الدقيقة ستون")[0] == {0: 1, 1: 1, 56: 1, 60: 1}
    assert numbers("hi", "लाल टीम 0, छप्पन मिनट, ५७")[0] == {0: 1, 56: 1, 57: 1}
    # "ein" / "un" / "един" / "एक" are also the article: counted apart, never as a number the translation added
    assert numbers("de", "Ein Pass von Olvholm") == ({}, 1) and numbers("fr", "les Bleus un") == ({}, 1)


def test_a_changed_dropped_or_added_number_is_caught():
    en = "Reds nil, Navy one, fifty-six minutes played."
    assert mismatch(en, "de", "Die Roten null, die Blauen eins, fünfundfünfzig Minuten gespielt.") == \
        ["number 56 missing", "number 55 added"]                       # the shipped c_0007, 27 Oct
    assert mismatch(en, "de", "Die Roten null, die Blauen eins, sechsundfünfzig Minuten gespielt.") == []
    assert mismatch(en, "fr", "Les Rouges zéro, les Bleus un, cinquante-six minutes jouées.") == []   # "un" may be 1
    assert mismatch(en, "es", "Los Rojos cero, los Azules, cincuenta y seis.") == ["number 1 missing"]
    assert mismatch("Still checking.", "fr", "Les deux camps attendent.") == ["number 2 added"]
    assert mismatch("A pass from Olvholm.", "de", "Ein Pass von Olvholm.") == []    # an article adds nothing
    players = ["Fenford"]
    assert L.check(en, "Die Roten null, die Blauen eins, fünfundfünfzig Minuten gespielt.", players, "de") == \
        ["number 56 missing", "number 55 added"]


@pytest.mark.parametrize("lang", sorted(L.LANGS))
def test_every_cached_translation_passes_the_number_check(lang):
    """The l10n cache is what a rebuild uses (cues and the offline answers): a line that fails here would be sent
    back to the model on the next build."""
    m = load_match("judge")
    players = sorted({p["last_name"] for side in ("home", "away") for p in m.meta["teams"][side]["players"]})
    bad = {en: tr for en, tr in L.load_cache(lang)["lines"].items() if L.check(en, tr, players, lang)}
    assert bad == {}


def test_the_hand_corrected_lines_are_shipped():
    cue = lambda lang, cid: next(json.loads(s) for s in (BUNDLE / "judge" / f"cues.{lang}.radio.jsonl")  # noqa: E731
                                 .read_text(encoding="utf-8").splitlines() if json.loads(s)["cue_id"] == cid)
    assert "sechsundfünfzig" in cue("de", "c_0007")["text"]["radio"]
    assert "ست وخمسون" in cue("ar", "c_0007")["text"]["radio"]
    assert "deux" not in cue("fr", "c_0005")["text"]["radio"]


# ---- 11. a bad playhead or argument never breaks a tool -----------------------------------------------------------
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, "abc", None, "nan", [1]])
def test_a_playhead_that_is_not_a_finite_number_is_the_cuts_start(bad):
    assert B.clamp(bad) == B.t0                         # +inf must not mean the end of the match
    for name, args in (("get_score_and_clock", {}), ("get_ball_position", {}), ("get_last_events", {"n": 2}),
                       ("get_recap", {}), ("what_did_i_miss", {"since": "56:10"})):
        r = call(name, args, bad, B)
        assert "say" in r and r["as_of_clock"] == B.clock_str(B.t0), (name, bad, r)


def test_the_session_keeps_working_after_a_nan_playhead():
    assert "say" in call_tool("get_score_and_clock", {}, playhead_s=math.nan, bundle=B)
    assert call_tool("get_score_and_clock", {}, playhead_s=REVEAL + 1, bundle=B)["say"].startswith("Reds nil, Navy one")


def test_get_last_events_takes_a_number_word_and_ignores_nonsense():
    p = 900.0
    assert len(call("get_last_events", {"n": "two"}, p, B)["evidence_ids"]) == 2
    assert len(call("get_last_events", {"n": "2"}, p, B)["evidence_ids"]) == 2
    for n in ("lots", math.nan, math.inf, None, 10 ** 400):
        r = call("get_last_events", {"n": n}, p, B)
        assert "say" in r and 1 <= len(r["evidence_ids"]) <= 5, (n, r)


def test_adjust_sound_never_turns_a_sound_off_for_a_nan():
    r = call("adjust_sound", {"sound": "crowd", "change": 5, "current": math.nan}, 900.0, B)
    assert r["say"] == "The crowd murmur, up by 5." and r["prefs"] == {"sound": "crowd", "change": 5}
    for args in ({"level": math.nan}, {"level": math.inf}, {"change": math.nan}, {"level": 10 ** 400}):
        r = call("adjust_sound", {"sound": "crowd", **args}, 900.0, B)
        assert r["error"] == "bad_arguments" and "prefs" not in r, (args, r)
    r = call("set_preferences", {"crowd_mix": math.nan}, 900.0, B)
    assert "crowd_mix" not in r["prefs"]               # max(0, NaN) is 0: it would have muted the crowd


# ---- 12. the ball while a shot's outcome is not out yet -----------------------------------------------------------
def test_ball_position_gives_nothing_away_while_a_shot_is_unrevealed():
    shots = [e for e in B.events if e["type"] == "shot"]
    for e in shots:
        s = B.sig(e["id"])
        for p in (s["t"], (s["t"] + s["reveal_t"]) / 2, s["reveal_t"] - 0.01):
            r = call("get_ball_position", {}, p, B)
            assert r["fragments"] == ["hold"] and "x" not in r and "y" not in r, (e["id"], p, r)
            assert all(B.sig(x)["reveal_t"] <= p for x in r["evidence_ids"])
        after = call("get_ball_position", {}, s["reveal_t"] + 0.01, B)
        assert after["fragments"] != ["hold"] and "x" in after
    # The VAR check of the goal (D28's live case, 56:34): no "out of play", no position inside the net.
    r = call("get_ball_position", {}, B.parse_clock("56:34"), B)
    assert "out of play" not in r["say"] and "x" not in r


def test_the_mcp_server_passes_no_ball_position_during_the_var_check():
    pytest.importorskip("mcp")
    from tely.qa import mcp_server

    p = B.parse_clock("56:34")
    out = mcp_server.tools.call("get_ball_position", {}, mcp_server.playhead_from({"x-tely-playhead": str(p)}, B), B)
    assert "x" not in out and "y" not in out


# ---- 13. wider outcome words ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("lang,text", [
    ("de", "Vaston hält!"), ("de", "abgewehrt!"), ("de", "drüber!"),
    ("es", "¡Fuera!"), ("es", "Vaston rechaza"), ("fr", "au-dessus !"), ("fr", "Vaston repousse"),
    ("bg", "Вастон отби!"), ("bg", "встрани!"),
])
def test_the_firewall_knows_the_wider_outcome_words(lang, text):
    assert L.outcome_said(lang, text)
