# OWNER: B (Nikolay). Stage 1 tests (BUILD_PLAN "Done when"): determinism, the two file 33 fixes, crowd spoiler
# safety and look-ahead, plus the clock, haptics and judge cut. The format itself is checked in test_contract.py.
from __future__ import annotations

import copy
import gzip
import hashlib
import json
import time
from pathlib import Path

import pytest

from audiostands import build_match, clock, crowd, interpret, judge_cut
from audiostands.generator import FPS, HALF_L, HALF_W, PERIODS, generate
from audiostands.movement import ball_rows

ROOT = Path(__file__).resolve().parents[3]
JUDGE = ROOT / "web" / "public" / "replay" / "v1" / "judge"
FILES = ("meta.json", "events.jsonl", "signals.json", "ticks.json.gz")
CUT = json.loads((ROOT / "pipeline" / "judge_cut.json").read_text(encoding="utf-8"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- determinism
@pytest.fixture(scope="module")
def two_builds(tmp_path_factory):
    outs = []
    for n in range(2):
        d = tmp_path_factory.mktemp(f"build{n}")
        t = time.perf_counter()
        build_match.build(CUT, d, report=False)
        outs.append((d, time.perf_counter() - t))
    return outs


def test_two_runs_give_identical_sha256(two_builds):
    (a, _), (b, _) = two_builds
    for name in FILES:
        assert sha(a / name) == sha(b / name), name


def test_committed_bundle_matches_a_fresh_build(two_builds):
    # SEAM(B->A): A's build_bundle reruns build_match; any byte difference would show up as a change in A's commits
    d, _ = two_builds[0]
    for name in ("meta.json", "events.jsonl", "signals.json"):
        assert sha(d / name) == sha(JUDGE / name), f"{name}: rerun python -m audiostands.build_match --cut judge"
    new, old = (gzip.decompress((p / "ticks.json.gz").read_bytes()) for p in (d, JUDGE))
    assert hashlib.sha256(new).digest() == hashlib.sha256(old).digest(), "ticks content differs"


def test_build_is_fast(two_builds):
    assert all(dt < 60 for _, dt in two_builds)          # BUILD_PLAN: under 60 s (the report adds a few seconds)


# ---------------------------------------------------------------- file 33 regressions
SEEDS = range(1, 11)


def test_goal_kick_after_a_miss_is_at_the_defending_end():
    """File 33 fix 1: after a shot goes wide, the goal kick is taken at the end the shot was aimed at."""
    checked = 0
    for s in SEEDS:
        evs = generate(s)["events"]
        for i, e in enumerate(evs):
            if e["type"] == "shot" and e["outcome_type"] in ("wide", "woodwork"):
                gk = next((x for x in evs[i + 1:] if x["type"] == "pass" and x["period"] == e["period"]), None)
                if gk is None:                                       # the half ended before the goal kick
                    continue
                assert gk["sub_type"] == "goal_kick" and gk["team"] != e["team"]
                assert gk["x"] * e["x_end"] > 0 and abs(gk["x"]) == pytest.approx(HALF_L - 5.5)
                checked += 1
    assert checked > 10


def test_passes_aimed_off_the_pitch_are_redrawn_not_clamped():
    """File 33 fix 2: passes stay inside the lines because they are re-drawn, so almost none sit on the clamp."""
    ends = [(e["x_end"], e["y_end"]) for s in SEEDS for e in generate(s)["events"] if e["type"] == "pass"]
    assert all(abs(x) <= HALF_L - 0.5 and abs(y) <= HALF_W - 0.5 for x, y in ends)
    clamped = sum(1 for x, y in ends if abs(x) == HALF_L - 0.5 or abs(y) == HALF_W - 0.5)
    assert clamped / len(ends) < 0.005


# ---------------------------------------------------------------- crowd: spoiler safety and look-ahead
def crowd_for(match: dict) -> dict:
    k = PERIODS.index(CUT["period"])
    t0, t1 = CUT["t_start"], CUT["t_end"]
    ball = ball_rows(match["periods"][k]["keys"], t0 * FPS, t1 * FPS)
    rows = interpret.per_second(match, k, t0, t1, ball)
    mo = crowd.moments(match["events"], k)
    return {end: crowd.crowd_states(rows, mo, end) for end in ("H", "A")}


def test_crowd_before_a_shot_does_not_depend_on_its_outcome():
    m = generate(CUT["seed"])
    base = crowd_for(m)
    shots = [e for e in m["events"] if e["type"] == "shot" and e["period"] == CUT["period"]
             and CUT["t_start"] * FPS <= e["f"] <= CUT["t_end"] * FPS]
    assert shots
    for shot in shots:
        flipped = copy.deepcopy(m)
        e = next(x for x in flipped["events"] if x["id"] == shot["id"])
        e["outcome_type"] = "saved" if e["outcome_type"] == "successful" else "successful"
        e["is_successful"] = e["outcome_type"] == "successful"
        other = crowd_for(flipped)
        n = int(shot["f"] / FPS) - CUT["t_start"]          # seconds strictly before the shot
        for end in ("H", "A"):
            assert other[end][:n] == base[end][:n], (shot["id"], end)


def test_look_ahead_swell_before_every_good_chance():
    sig = json.loads((JUDGE / "signals.json").read_text(encoding="utf-8"))
    rows = {r["t"]: r for r in sig["per_second"]}
    checked = 0
    for eid, s in sig["events"].items():
        if s["xg"] is not None and s["xg"] >= 0.1 and int(s["t"]) - 8 in rows:
            now, then = rows[int(s["t"])]["crowd"]["H"], rows[int(s["t"]) - 8]["crowd"]["H"]
            # BUILD_PLAN: +0.2 over 8 s. Excitement is capped at 1, so when the crowd is already near the top
            # (a second chance right after a first) it must use at least 80% of the room it has left.
            need = min(0.2, 0.8 * (1 - then["excitement"]))
            assert now["excitement"] >= then["excitement"] + need, eid
            checked += 1
    assert checked >= 1


def test_valence_has_opposite_signs_after_a_goal():
    sig = json.loads((JUDGE / "signals.json").read_text(encoding="utf-8"))
    events = [json.loads(s)["event"] for s in (JUDGE / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = {r["t"]: r for r in sig["per_second"]}
    goals = [e for e in events if e["type"] == "shot" and e["outcome_type"] == "successful"]
    assert goals
    for g in goals:
        r = rows[int(sig["events"][g["id"]]["reveal_t"]) + 2]["crowd"]
        assert r["H"]["valence"] * r["A"]["valence"] < 0


def test_one_shots_and_outcome_tactons_never_come_before_the_reveal():
    sig = json.loads((JUDGE / "signals.json").read_text(encoding="utf-8"))
    reveals = sorted(s["reveal_t"] for s in sig["events"].values() if s["xg"] is not None)
    for o in sig["crowd_one_shots"]:
        if o["kind"] in ("roar", "stunned_hush", "ooh_groan", "relief_applause"):
            assert o["t"] in reveals
    for h in sig["haptics"]:
        if h["tacton"] in ("goal", "nearMiss"):
            assert h["t"] in reveals


# ---------------------------------------------------------------- clock (file 43)
def test_clock_firewall():
    clk = clock.Clock(t0_wall=1000.0)
    evs = [{"t": 5.0}, {"t": 15.0}, {"t": 25.0}]
    now = 1000.0 + 20.0                                    # truth 20 s, playhead 10 s
    assert clock.qa_view(evs, clk, now) == [{"t": 5.0}]
    assert clock.director_window(evs, clk, now) == [{"t": 15.0}]
    cues = [{"cue_id": "c1", "t_in": 12.0, "utterance": {"ssml": "<speak/>", "audio_url": "a.mp3"}},
            {"cue_id": "c2", "t_in": 14.0, "utterance": {}}]
    sent = set()
    out = clock.release(cues, clk, now, sent)
    assert [c["cue_id"] for c in out] == ["c1"] and "ssml" not in out[0]["utterance"]
    assert clock.release(cues, clk, now, sent) == []


# ---------------------------------------------------------------- judge cut
def test_judge_cut_is_the_first_qualifying_window():
    assert judge_cut.find(range(1, CUT["seed"] + 1)) == CUT
    meta = json.loads((JUDGE / "meta.json").read_text(encoding="utf-8"))
    assert meta["judge_cut"]["seed"] == CUT["seed"] and meta["judge_cut"]["t_start"] == CUT["t_start"]
    assert meta["judge_cut"]["score_at_start"] == {"home": 0, "away": 0}
