# Stage 5 Director checks. No Azure: the Foundry Director is replayed from the reply file
# recorded on 23 Oct 2026 (tely/agents/recorded/judge.json), and failures are simulated.
import asyncio
import copy
import json
import random
import re

import pytest

from tely import build_bundle, build_commentary, spoiler
from tely.agents import director as D
from tely.agents import rules_director
from tely.agents import workflow as W
from tely.commentary import planner
from tely.commentary.source import load_match
from tely.spoiler import OUTCOME

CUTS = ["sample", "judge"]
RECORDED = build_bundle.recorded("judge")


class FakeSynth:
    def __init__(self):
        self.calls = 0

    def synthesise(self, doc):
        self.calls += 1
        text = re.sub(r"<[^>]+>|\[\w+\]", "", doc)
        pause = sum(int(ms) for ms in re.findall(r'<break time="(\d+)ms"', doc)) / 1000
        return b"ID3fake", planner.estimate(text, "", 0) * 1.15 + pause


class FakeModel:
    """A Director model that answers from a function, or raises (simulated 429 / timeout)."""

    name = "fake@test"

    def __init__(self, answer):
        self.answer, self.asked = answer, []

    async def ask(self, key, feat):
        self.asked.append(key)
        out = self.answer(key, feat)
        if isinstance(out, Exception):
            raise out
        return D.Reply(out if isinstance(out, str) else json.dumps(out), 1.0, {"input": 400, "output": 40})


@pytest.fixture(scope="module", params=CUTS)
def cut(request):
    return request.param


@pytest.fixture(scope="module")
def match(cut):
    return load_match(cut)


def good(**kw):
    return {"build_up_level": 0.7, "lead_s": 4.0, "hold_ms": 200, "hint_type": "danger", **kw}


# --- schema / Verifier ---------------------------------------------------------------------------------------------

def test_valid_plan_passes_the_verifier():
    feat = {"events": [], "shot": {"xg": 0.2}}
    assert D.validate(good(), feat) == D.Plan(0.7, 4.0, 200, "danger")


@pytest.mark.parametrize("reply, why", [
    # The very first live reply on 23 Oct, before the instructions gave ranges: the Verifier must reject it.
    ({"build_up_level": 2, "lead_s": 1, "hold_ms": 1200, "hint_type": "counter"}, "outside"),
    (good(build_up_level=-0.1), "outside"),
    (good(lead_s=6.0), "outside"),
    (good(hold_ms=200.5), "integer"),
    (good(hold_ms=True), "integer"),
    (good(build_up_level="high"), "number"),
    (good(hint_type="goal"), "hint_type"),
    ({**good(), "outcome": "goal"}, "fields"),
    ({k: v for k, v in good().items() if k != "lead_s"}, "fields"),
    ([good()], "not an object"),
])
def test_verifier_rejects_anything_outside_the_schema(reply, why):
    with pytest.raises(D.PlanError, match=why):
        D.validate(reply, {"events": [], "shot": {"xg": 0.2}})


def test_verifier_rejects_a_hint_the_window_does_not_support():
    feat = {"events": [{"type": "pass", "sub_type": None, "team": "attacking"}], "shot": {"xg": 0.2}}
    with pytest.raises(D.PlanError, match="counter"):
        D.validate(good(hint_type="counter"), feat)
    with pytest.raises(D.PlanError, match="set_piece"):
        D.validate(good(hint_type="set_piece"), feat)
    feat["events"] += [{"type": "defending", "sub_type": "interception", "team": "attacking"},
                       {"type": "pass", "sub_type": "free_kick", "team": "attacking"}]
    assert D.validate(good(hint_type="counter"), feat).hint_type == "counter"
    assert D.validate(good(hint_type="set_piece"), feat).hint_type == "set_piece"


def test_parse_accepts_a_fenced_reply_and_rejects_prose():
    assert D.parse("```json\n" + json.dumps(good()) + "\n```", {"events": []}).lead_s == 4.0
    with pytest.raises(D.PlanError, match="not JSON"):
        D.parse("Big chance coming, build it up!", {"events": []})


def test_schema_and_ranges_agree():
    props = D.SCHEMA["properties"]
    assert set(D.SCHEMA["required"]) == set(props) and D.SCHEMA["additionalProperties"] is False
    assert (props["lead_s"]["minimum"], props["lead_s"]["maximum"]) == D.LEAD_RANGE
    assert props["hint_type"]["enum"] == list(D.HINTS)


# --- the firewall --------------------------------------------------------------------------------------------------

def shots(m):
    return [e for e in m.events if e["type"] == "shot"]


def test_features_are_identical_for_a_goal_and_a_miss(match):
    """File 43 §2: the Director must never see an outcome. Rewrite every shot's ending; the features must not move."""
    for k, shot in enumerate(shots(match)):  # one shot at a time: earlier results are the past, and may be known
        other = copy.deepcopy(match)
        e = shots(other)[k]
        e.update(outcome_type="wide" if e["outcome_type"] == "successful" else "successful",
                 is_successful=not e.get("is_successful"), x_end=0.0, y_end=0.0, related_event_ids=[],
                 var={"reviewed": True, "upheld": False})
        other.sig(e["id"]).update(reveal_t=other.sig(e["id"])["reveal_t"] + 5, spoken="X scores!",
                                  spoken_past="X scored")
        assert D.features(match, shot) == D.features(other, e)


def test_features_hold_no_outcome_words_and_stay_small(match):
    for e in shots(match):
        feat = D.features(match, e)
        text = json.dumps(feat).lower()
        assert not set(re.findall(r"[a-z]+", text)) & OUTCOME
        assert "outcome" not in text and "reveal" not in text and "spoken" not in text
        assert all(ev["in_s"] < feat["shot"]["in_s"] for ev in feat["events"])  # nothing after the shot
        assert len(D.INSTRUCTIONS) / 4 + len(D.prompt(feat)) / 3 + 60 < 1200  # file 43: prompt + output <= 1,200 tokens


# --- fallbacks -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("error", [RuntimeError("Error code: 429 - Too Many Requests"), asyncio.TimeoutError(),
                                   RuntimeError("DeploymentNotFound: no quota")])
def test_model_failure_falls_back_to_rules_and_is_recorded(match, error):
    model = FakeModel(lambda k, f: error)
    run = W.direct(match, model, None, "foundry")
    rules = W.direct(match, None, None, "rules")
    assert run.plans == rules.plans
    called = [s for s in run.steps if s.window.call]
    assert called and all(s.director == rules_director.NAME and s.fallback.startswith("model:") for s in called)
    assert run.summary()["fallbacks_after_a_call"] == len(called)


def test_rejected_reply_falls_back_to_rules(match):
    run = W.direct(match, FakeModel(lambda k, f: good(lead_s=9.0)), None, "foundry")
    assert all(s.director == rules_director.NAME and s.fallback.startswith("verifier:")
               for s in run.steps if s.window.call)


def test_at_most_one_director_call_per_10_s():
    m = load_match("judge")
    a, b = shots(m)[-2:]
    close = copy.deepcopy(m)
    close.sig(b["id"])["t"] = close.sig(a["id"])["t"] + 5.0
    model = FakeModel(lambda k, f: good())
    run = W.direct(close, model, None, "foundry")
    assert b["id"] not in model.asked
    step = next(s for s in run.steps if s.window.key == b["id"])
    assert step.director == rules_director.NAME and step.fallback.startswith("budget")
    times = [s.window.t_shot for s in run.steps if s.window.call]
    assert all(t1 - t0 >= W.CALL_EVERY_S for t0, t1 in zip(times, times[1:]))


def test_rules_director_reproduces_stage_3_exactly(cut, match, tmp_path):
    build_commentary.build(cut, tmp_path / "a", lambda: FakeSynth())
    build_commentary.build(cut, tmp_path / "b", lambda: FakeSynth(), plans=W.direct(match, None).plans)
    read = lambda p: [(c["t_in"], c["text"]["radio"], c["utterance"]["ssml_sha256"])  # noqa: E731
                      for c in map(json.loads, (p / "cues.en.radio.jsonl").read_text(encoding="utf-8").splitlines())]
    assert read(tmp_path / "a") == read(tmp_path / "b")


# --- DIRECTOR=foundry from the recorded replies ----------------------------------------------------------------------

def test_recorded_replies_still_match_todays_windows():
    """If B's match changes, the replay stops matching: re-record with DIRECTOR=foundry."""
    run = W.direct(load_match("judge"), D.ReplayDirector(RECORDED), None, "replay")
    assert run.summary()["fallbacks"] == 0
    assert all(s.director.startswith(D.VERSION) for s in run.steps)
    rec = json.loads(RECORDED.read_text(encoding="utf-8"))
    assert "eyJ" not in RECORDED.read_text(encoding="utf-8")  # no bearer tokens in the fixture
    assert all(c["tokens"]["input"] + c["tokens"]["output"] <= 1200 for c in rec["calls"])


def test_spoiler_leaks_still_empty_with_the_foundry_director(tmp_path):
    m = load_match("judge")
    run = W.direct(m, D.ReplayDirector(RECORDED), None, "replay")
    rep = build_commentary.build("judge", tmp_path, lambda: FakeSynth(), plans=run.plans,
                                 directors={s.window.key: s.director for s in run.steps})
    assert rep["spoiler_leaks"] == [] and not rep["failed"]
    cues = [json.loads(s) for s in (tmp_path / "cues.en.radio.jsonl").read_text(encoding="utf-8").splitlines()]
    assert spoiler.spoiler_leaks(cues, spoiler.flat_events(m)) == []
    builds = [c for c in cues if c["kind"] == "build"]
    assert builds and all(c["source"]["director"].startswith(D.VERSION) for c in builds)
    for c in builds:  # lead_s is held to LEAD_S ± 0.5 by the schema (Stage 3 check)
        shot = m.by_id(c["evidence"][0])
        assert 3.5 - 1e-6 <= m.t(shot) - c["t_in"] <= 4.5 + 0.5 + 1e-6


def test_any_valid_plan_keeps_the_firewall(cut, match, tmp_path):
    """Property: whatever a schema-valid Director says (6 random plans per shot, seeded), no line leaks an outcome
    and every line passes truth_check. The plan has no field that could carry a result."""
    rng = random.Random(5)

    def answer(key, feat):
        hints = ["danger", "none"] + (["counter"] if D.regained(feat) else []) + (["set_piece"] if D.set_piece(feat) else [])
        return {"build_up_level": round(rng.random(), 2), "lead_s": round(rng.uniform(*D.LEAD_RANGE), 1),
                "hold_ms": rng.randrange(0, 801, 50), "hint_type": rng.choice(hints)}

    for k in range(6):
        run = W.direct(match, FakeModel(answer), None, "foundry")
        assert run.summary()["fallbacks_after_a_call"] == 0
        rep = build_commentary.build(cut, tmp_path / str(k), lambda: FakeSynth(), plans=run.plans)
        assert rep["spoiler_leaks"] == [] and not rep["failed"], rep["failed"]


# --- engines -------------------------------------------------------------------------------------------------------

def test_agent_framework_graph_and_plain_runner_agree(monkeypatch):
    pytest.importorskip("agent_framework")  # only on A's machine: CI never installs requirements-azure.txt
    m = load_match("judge")
    af = W.direct(m, D.ReplayDirector(RECORDED), None, "replay")
    monkeypatch.setenv("TELY_NO_AF", "1")
    plain = W.direct(m, D.ReplayDirector(RECORDED), None, "replay")
    assert (af.engine, plain.engine) == ("agent-framework", "plain")
    strip = lambda r: [{k: v for k, v in x.items() if not k.endswith("_ms")} for x in r.summary()["log"]]  # noqa: E731
    assert strip(af) == strip(plain)


def test_build_bundle_uses_the_director(tmp_path):
    out = tmp_path
    for f in ("meta.json", "events.jsonl", "signals.json", "ticks.json.gz"):
        (out / f).write_bytes((build_bundle.BUNDLE / "judge" / f).read_bytes())
    rep = build_bundle.build("judge", out, lambda: FakeSynth(), run_match=lambda c, o: None,
                             run_segments=lambda c, o: "skipped: test", director="replay",
                             model=D.ReplayDirector(RECORDED))
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert man["director"].startswith(D.VERSION) and rep["director"]["model_plans"] == rep["director"]["windows"]


def test_committed_build_ups_end_by_their_shot_and_keep_the_call():
    """Real Brian durations: a longer Director tail once ran 1.5 s past the shot and pushed out the call (23 Oct)."""
    m = load_match("judge")
    cues = [json.loads(s) for s in (build_bundle.BUNDLE / "judge" / "cues.en.radio.jsonl").read_text(
        encoding="utf-8").splitlines()]
    builds = [c for c in cues if c["kind"] == "build"]
    assert builds
    for c in builds:
        shot = m.by_id(c["evidence"][0])
        assert c["t_in"] + c["utterance"]["duration_ms"] / 1000 <= m.t(shot) + 1e-6, c["text"]["radio"]
    calls = {c["evidence"][0] for c in cues if c["kind"] == "call"}
    assert any(c["evidence"][0] in calls for c in builds)  # the headed goal keeps "Fenford, the header!"
