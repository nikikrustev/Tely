# OWNER: A (potencialbg). Stage 3 commentary checks. The synthesiser is mocked: CI never calls Azure.
import json
import re

import pytest

from audiostands import build_commentary, spoiler
from audiostands.commentary import planner, ssml, templates, verifier
from audiostands.commentary.source import MATCH_DIRS, load_match


class FakeSynth:
    """Deterministic stand-in for Azure Speech: duration from the words, a little slower than the estimate."""

    def __init__(self):
        self.calls = 0

    def synthesise(self, doc: str):
        self.calls += 1
        text = re.sub(r"<[^>]+>|\[\w+\]", "", doc)
        return b"ID3fake-mp3", planner.estimate(text, "", 0) * 1.15 + (0.3 if "<break" in doc else 0)


@pytest.fixture(scope="module")
def match():
    return load_match("judge")


@pytest.fixture(scope="module")
def built(tmp_path_factory, match):
    out = tmp_path_factory.mktemp("judge")
    fake = FakeSynth()
    rep = build_commentary.build("judge", out, lambda: fake)
    cues = [json.loads(s) for s in (out / "cues.en.radio.jsonl").read_text(encoding="utf-8").splitlines()]
    return {"out": out, "rep": rep, "cues": cues, "fake": fake}


# --- the five BUILD_PLAN Stage 3 checks --------------------------------------------------------------------------

def test_spoiler_leaks_is_empty(built, match):
    assert built["rep"]["spoiler_leaks"] == []
    assert spoiler.spoiler_leaks(built["cues"], spoiler.flat_events(match)) == []
    assert all(c["spoiler_check"] == "pass" for c in built["cues"])


def test_truth_check_passes_for_every_line(built):
    assert built["rep"]["failed"] == []
    assert all(c["truth_check"] == "pass" for c in built["cues"])
    assert built["rep"]["truth_check_pass"] == f"{len(built['cues'])}/{len(built['cues'])}"


def test_every_build_line_starts_lead_s_before_its_shot(built, match):
    builds = [c for c in built["cues"] if c["kind"] == "build"]
    for c in builds:
        shot_t = match.t(match.by_id(c["evidence"][0]))
        assert abs((shot_t - c["t_in"]) - templates.LEAD_S) <= 0.5, c
    # and no build-up was dropped: every chance over the xG threshold gets one (file 39: same for goals and saves)
    chances = {e["id"] for e in match.events
               if e["type"] == "shot" and (match.sig(e["id"])["xg"] or 0) >= templates.BUILD_MIN_XG}
    assert {c["evidence"][0] for c in builds} == chances and chances


def test_no_two_lines_overlap(built):
    cues = sorted(built["cues"], key=lambda c: c["t_in"])
    for a, b in zip(cues, cues[1:]):
        assert a["t_in"] + a["utterance"]["duration_ms"] / 1000 <= b["t_in"] + 1e-3, (a["cue_id"], b["cue_id"])


def test_second_build_makes_zero_tts_calls(built):
    before = (built["out"] / "cues.en.radio.jsonl").read_bytes()
    again = FakeSynth()
    rep = build_commentary.build("judge", built["out"], lambda: again)
    assert again.calls == 0 and rep["tts_calls"] == 0
    assert (built["out"] / "cues.en.radio.jsonl").read_bytes() == before  # deterministic


# --- radio rules (file 36, file 39) ------------------------------------------------------------------------------

def test_never_more_than_20_s_between_lines(built, match):
    starts = [match.t_start] + sorted(c["t_in"] for c in built["cues"]) + [match.t_end]
    assert max(b - a for a, b in zip(starts, starts[1:])) <= planner.MAX_QUIET_S


def test_intro_gives_both_kits_and_directions(built, match):
    intro = built["cues"][0]
    assert intro["kind"] == "intro" and intro["t_in"] == match.t_start
    text = intro["text"]["radio"]
    for side in ("home", "away"):
        assert match.meta["teams"][side]["kit"]["words"] in text
    assert "to your right" in text and "to your left" in text
    assert text.startswith("AI commentary")  # every AI voice is labelled as AI (CLAUDE.md)


def test_goal_call_names_the_scorer_only_after_the_play(built, match):
    goal = next(e for e in match.events if e["type"] == "shot" and e["outcome_type"] == "successful")
    scorer = match.surname(goal["player_id"])
    react = next(c for c in built["cues"] if c["kind"] == "react" and c["evidence"][0] == goal["id"])
    detail = next(c for c in built["cues"] if c["kind"] == "detail" and c["evidence"][0] == goal["id"])
    assert scorer not in react["text"]["radio"]
    text = detail["text"]["radio"]
    assert text.index(scorer) > text.index("cross")  # the play first, then the name
    assert react["t_in"] >= match.reveal_t(goal) and react["utterance"]["style"] == "shouting"


def test_cue_contract_fields_and_files(built):
    out = built["out"]
    for c in built["cues"]:
        assert {"cue_id", "tc_in", "t_in", "kind", "reveal", "text", "utterance", "crowd_state", "haptic", "spatial",
                "evidence", "truth_check", "spoiler_check", "source"} <= set(c)
        assert "ssml" not in c["utterance"]  # the release gate strips SSML (file 43)
        assert re.fullmatch(r"\d\d:\d\d:\d\d:\d\d", c["tc_in"])
        assert (out / c["utterance"]["audio_url"]).is_file()
    assert (out / "captions_sdh.vtt").read_text(encoding="utf-8").startswith("WEBVTT")
    assert (out / "descriptions.vtt").read_text(encoding="utf-8").startswith("WEBVTT")


def test_sdh_captions_carry_crowd_sounds_and_speaker(built):
    vtt = (built["out"] / "captions_sdh.vtt").read_text(encoding="utf-8")
    assert "AI COMMENTATOR: " in vtt
    assert "[Reds end roars]" in vtt and "[Navy end falls silent]" in vtt
    assert "\r" not in vtt


def test_spoiler_lift_is_reported(built):
    lift = built["rep"]["spoiler_lift"]
    assert lift["n"] == 2 and lift["p_goal_given_build"] == 0.5 and lift["mean_xg"] == 0.2


# --- the seam with B ---------------------------------------------------------------------------------------------

def test_loader_reads_the_sample_until_b_merges_the_judge_cut(match):
    assert MATCH_DIRS["judge"].parts[-3:] == ("contracts", "b", "sample")  # one line to switch
    assert len(match.events) == 24 and match.meta["synthetic"] is True


def test_zone_rule_matches_b_signals(match):
    for e in match.events:
        attacks = match.meta["teams"][match.side(e)]["attacks"]
        assert templates.zone(e["x"], e["y"], attacks)["words"] == match.sig(e["id"])["zone"]["words"], e["id"]


def test_score_and_holder_are_never_known_early(match):
    goal = next(e for e in match.events if e["type"] == "shot" and e["outcome_type"] == "successful")
    assert match.score_at(match.reveal_t(goal) - 0.01) == {"home": 0, "away": 0}
    assert match.score_at(match.reveal_t(goal)) == {"home": 1, "away": 0}
    p = match.events[1]  # a pass in the air: the receiver is its outcome
    assert match.holder_at((match.t(p) + match.reveal_t(p)) / 2) == (None, None)


# --- the verifier catches what it should -------------------------------------------------------------------------

def test_truth_check_catches_wrong_score_name_number_and_digits(match):
    shot = match.by_id("e0011")
    assert verifier.truth_check(match, "Reds one, Navy nil, inside the first minute.", 30.0, []) != []
    assert verifier.truth_check(match, "Reds nil, Navy nil, inside the first minute.", 30.0, []) == []
    assert verifier.truth_check(match, "Hale has it.", 30.0, [shot["id"]])  # Hale is not in this event
    assert verifier.truth_check(match, "Reds nil, Navy nil, seven minutes played.", 30.0, [])
    assert verifier.truth_check(match, "Reds 0, Navy 0.", 30.0, [])
    assert verifier.truth_check(match, "Three passes in a row.", 30.0, [])


def test_spoiler_check_and_leak_eval_catch_an_early_outcome(match):
    shot = match.by_id("e0011")
    early = match.t(shot) - 2
    assert verifier.spoiler_check(match, "Saved!", early, [shot["id"]])
    leak = [{"cue_id": "x", "t_in": early, "text": {"radio": "What a save!"}, "kind": "build", "evidence": [shot["id"]]}]
    assert spoiler.spoiler_leaks(leak, spoiler.flat_events(match)) == [("x", "e0011")]
    in_flight = (match.t(shot) + match.reveal_t(shot)) / 2  # stricter than file 43: until the reveal
    leak[0]["t_in"] = in_flight
    assert spoiler.spoiler_leaks(leak, spoiler.flat_events(match)) == [("x", "e0011")]


def test_build_wording_depends_on_xg_not_outcome(match):
    shot = match.by_id("e0024")
    flipped = {**shot, "outcome_type": "saved", "is_successful": False}
    assert templates.build(match, shot).texts == templates.build(match, flipped).texts


# --- SSML (files 39 §4, 43 §7) -----------------------------------------------------------------------------------

def test_style_bands():
    assert [ssml.band(i) for i in (0.1, 0.3, 0.6, 0.8, 1.0)] == list(ssml.BANDS)


def test_dragonhd_ssml_uses_style_tags_only():
    doc = ssml.build_ssml("Saved! Solvang & co hold on.", "excited", pause_after_ms=300)
    assert doc.count("[excited]") == 2  # one per sentence: a tag ends at a sentence boundary
    assert "&amp;" in doc and '<break time="300ms"/>' in doc and "temperature=0.4" in doc
    assert "<prosody" not in doc and "express-as" not in doc
    assert "<break" not in ssml.build_ssml("Calm.", "calm")
    with pytest.raises(ValueError):
        ssml.build_ssml("x", "ecstatic")
    assert ssml.ssml_sha256(doc) == ssml.ssml_sha256(doc) and len(ssml.ssml_sha256(doc)) == 64
