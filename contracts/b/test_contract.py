"""Contract test for contracts/b/ (match format v0.1.0): checks the 90 s sample against the format.

    pip install -r contracts/b/requirements.txt
    pytest contracts/b

Moves to pipeline/tests/b/ once Stage 1 exists; there it should also run on the real judge cut.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

import pytest

import make_sample

HERE = Path(__file__).resolve().parent
SAMPLE = HERE / "sample"
HALF_L, HALF_W, GOAL_HALF_W = 52.5, 34.0, 3.66
MAX_BALL_MS = 40.0       # m/s = 144 km/h: our sanity cap for the ball, not a cited figure
MAX_PLAYER_MS = 10.3     # m/s = 37.1 km/h, the fastest top speed cited in file 19 (premierleague.com, Mar 2025)
TOUCH_M = 1.5            # an on-ball event's player must be this close to the ball at that moment


def load(d: Path = SAMPLE):
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    lines = [json.loads(s) for s in (d / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    signals = json.loads((d / "signals.json").read_text(encoding="utf-8"))
    ticks = json.loads(gzip.decompress((d / "ticks.json.gz").read_bytes()))
    return meta, lines, signals, ticks


META, LINES, SIGNALS, TICKS = load()
EVENTS = [ln["event"] for ln in LINES]
KICKOFF = datetime.fromisoformat(META["match"]["kickoff_time"])


def t_of(iso: str) -> float:
    return (datetime.fromisoformat(iso) - KICKOFF).total_seconds()


def on_pitch(x: float, y: float) -> bool:
    return abs(x) <= HALF_L and abs(y) <= HALF_W


def in_goal(x: float, y: float) -> bool:      # behind the goal line, inside the goal mouth (net depth ~2 m)
    return HALF_L < abs(x) <= HALF_L + 2.0 and abs(y) <= GOAL_HALF_W


def ball_at(t: float):
    rows, hz = TICKS["ball"]["rows"], TICKS["ball"]["hz"]
    return rows[round(t * hz)]


def player_at(pid: str, t: float):
    p = TICKS["players"]
    j, k = p["ids"].index(pid), round(t * p["hz"])
    return p["rows"][k][2 * j], p["rows"][k][2 * j + 1]


# ---------------------------------------------------------------- CDF
def test_events_are_valid_cdf_extreme():
    cdf = pytest.importorskip("cdf", reason="pip install -r contracts/b/requirements.txt")
    assert cdf.VERSION == META["cdf_version"] == "0.3.2"
    # extreme = unknown keys fail too, so none of our extras can sneak into the CDF lines (file 26 §2)
    cdf.EventSchemaValidator().validate_schema(sample=str(SAMPLE / "events.jsonl"), mode="extreme", limit=None)


def test_ids_agree_across_files():
    roster = {p["id"]: side for side, t in META["teams"].items() for p in t["players"]}
    team_ids = {t["id"]: side for side, t in META["teams"].items()}
    assert len({e["id"] for e in EVENTS}) == len(EVENTS)
    for ln in LINES:
        e = ln["event"]
        assert ln["match"]["id"] == META["match"]["id"]
        assert roster[e["player_id"]] == team_ids[e["team_id"]]          # the validator skips this (file 26)
        if e["receiver_id"] is not None:
            assert roster[e["receiver_id"]] == team_ids[e["receiver_team_id"]]
        for rel in e["related_event_ids"] or []:
            assert rel in {x["id"] for x in EVENTS}
    assert SIGNALS["match_id"] == TICKS["match_id"] == META["match"]["id"]
    assert TICKS["players"]["ids"] == [p["id"] for side in ("home", "away") for p in META["teams"][side]["players"]]
    numbers = [(side, p["jersey_number"]) for side, t in META["teams"].items() for p in t["players"]]
    assert len(set(numbers)) == len(numbers)


# ---------------------------------------------------------------- signals
def test_every_event_has_matching_signals():
    sig = SIGNALS["events"]
    assert list(sig) == [e["id"] for e in EVENTS]                      # same ids, same order
    for e in EVENTS:
        s = sig[e["id"]]
        assert s["t"] == pytest.approx(t_of(e["time"]), abs=1e-6)
        assert s["reveal_t"] >= s["t"]
        if e["receiver_time"]:
            assert s["reveal_t"] == pytest.approx(t_of(e["receiver_time"]), abs=1e-6)
        if e["type"] == "shot":
            assert 0 < s["xg"] < 1
        else:
            assert s["xg"] is None
        assert s["priority"] in (0, 1, 2, 3)
        assert s["zone"]["third"] in ("defensive_third", "middle_third", "attacking_third")
        assert s["zone"]["side"] in ("near", "centre", "far")
        assert isinstance(s["zone"]["in_box"], bool) and s["zone"]["words"]
        assert s["spoken"].strip() and s["spoken_past"].strip()


def test_per_second_signals_cover_the_window_in_range():
    cut = META["judge_cut"]
    rows = SIGNALS["per_second"]
    assert SIGNALS["hz"] == 1
    assert [r["t"] for r in rows] == list(range(int(cut["t_start"]), int(cut["t_end"]) + 1))
    for r in rows:
        assert sum(r["win_prob"].values()) == pytest.approx(1.0, abs=0.002)
        assert r["suspense"] >= 0 and 0 <= r["tension"] <= 1
        assert all(0 <= v <= 1 for v in r["danger"].values())
        for end in ("H", "A"):
            c = r["crowd"][end]
            assert 0 <= c["excitement"] <= 1 and -1 <= c["valence"] <= 1 and -1 <= c["danger"] <= 1
    for o in SIGNALS["crowd_one_shots"]:
        assert o["end"] in ("H", "A") and cut["t_start"] <= o["t"] <= cut["t_end"]


# ---------------------------------------------------------------- ticks
def test_ticks_cover_the_full_window_at_the_right_rates():
    cut = META["judge_cut"]
    dur = cut["t_end"] - cut["t_start"]
    assert TICKS["t0"] == cut["t_start"] and TICKS["duration_s"] == dur
    ball, players = TICKS["ball"], TICKS["players"]
    assert ball["hz"] == META["rates"]["ball_hz"] == 25
    assert players["hz"] == META["rates"]["player_hz"] and players["hz"] >= 1      # where_is needs >= 1 Hz
    assert len(ball["rows"]) == round(dur * ball["hz"]) + 1                       # both ends included
    assert len(players["rows"]) == round(dur * players["hz"]) + 1
    assert ball["columns"] == ["x", "y", "z", "alive", "poss"]
    assert all(len(r) == 5 and r[3] in (0, 1) and r[4] in ("home", "away", None) for r in ball["rows"])
    assert all((r[4] is not None) == (r[3] == 1) for r in ball["rows"])             # live ball <=> someone has it
    assert all(len(r) == 2 * len(players["ids"]) for r in players["rows"])


# ---------------------------------------------------------------- time order
def test_timestamps_are_in_order_and_utc():
    times = [t_of(e["time"]) for e in EVENTS]
    assert times == sorted(times)
    for e in EVENTS:
        assert e["time"].endswith("Z")                                          # file 26: UTC only
        t = t_of(e["time"])
        cs = round(t * 100)
        assert e["match_clock"] == f"{cs // 6000:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"
        if e["receiver_time"]:
            assert t_of(e["receiver_time"]) > t
    cut = META["judge_cut"]
    assert cut["t_start"] <= times[0] and times[-1] <= cut["t_end"]


# ---------------------------------------------------------------- positions and motion
def test_positions_stay_on_the_pitch():
    for e in EVENTS:
        assert on_pitch(e["x"], e["y"]), e["id"]
        if e["x_end"] is not None:
            assert on_pitch(e["x_end"], e["y_end"]) or (e["type"] == "shot" and in_goal(e["x_end"], e["y_end"]))
    for x, y, z, alive, _ in TICKS["ball"]["rows"]:
        assert on_pitch(x, y) or in_goal(x, y)                                  # in the net after a goal
        assert 0.0 < z <= 15.0
    for r in TICKS["players"]["rows"]:
        assert all(on_pitch(r[i], r[i + 1]) for i in range(0, len(r), 2))


def test_speeds_are_realistic():
    rows, hz = TICKS["ball"]["rows"], TICKS["ball"]["hz"]
    vb = max(math.hypot(b[0] - a[0], b[1] - a[1]) * hz for a, b in zip(rows, rows[1:]))
    assert 5.0 < vb <= MAX_BALL_MS
    p = TICKS["players"]
    for j, pid in enumerate(p["ids"]):
        v = max(math.hypot(b[2 * j] - a[2 * j], b[2 * j + 1] - a[2 * j + 1]) * p["hz"]
                for a, b in zip(p["rows"], p["rows"][1:]))
        assert v <= MAX_PLAYER_MS, f"{pid} runs at {v:.1f} m/s"


def test_events_line_up_with_the_ball_and_players():
    for e in EVENTS:
        t = t_of(e["time"])
        bx, by = ball_at(t)[:2]
        assert math.hypot(bx - e["x"], by - e["y"]) < 0.05, e["id"]             # ball is where the event says
        px, py = player_at(e["player_id"], t)                                  # nearest 5 Hz row (<= 0.1 s away)
        assert math.hypot(px - e["x"], py - e["y"]) <= TOUCH_M, e["id"]
        if e["receiver_time"]:
            rx, ry = ball_at(t_of(e["receiver_time"]))[:2]
            assert math.hypot(rx - e["x_end"], ry - e["y_end"]) < 0.05, e["id"]


# ---------------------------------------------------------------- the story
def test_sample_tells_the_required_story():
    types = [(e["type"], e["sub_type"], e["outcome_type"], e["team_id"]) for e in EVENTS]
    run = best = 0
    for prev, cur in zip([None] + types, types):
        ok = cur[0] == "pass" and cur[2] == "successful"
        run = run + 1 if ok and prev and prev[0] == "pass" and prev[3] == cur[3] and prev[2] == "successful" else int(ok)
        best = max(best, run)
    assert best >= 3, "pass chain"
    assert any(t[0] == "shot" for t in types), "shot"
    assert any(t[0] == "goalkeeping" and t[1] == "save" for t in types), "save"
    goals = [e for e in EVENTS if e["type"] == "shot" and e["outcome_type"] == "successful"]
    assert goals, "goal"
    g = goals[0]
    side = next(s for s, t in META["teams"].items() if t["id"] == g["team_id"])
    reveal = SIGNALS["events"][g["id"]]["reveal_t"]
    rows = SIGNALS["per_second"]
    before = [r for r in rows if r["t"] < reveal]
    after = [r for r in rows if r["t"] >= reveal]
    assert all(r["score"][side] == 0 for r in before)                          # no score leak before the goal
    assert all(r["score"][side] == 1 for r in after)
    assert after[0]["win_prob"][side] > before[-1]["win_prob"][side] + 0.1


# ---------------------------------------------------------------- determinism
def test_regenerating_gives_identical_files(tmp_path):
    make_sample.write(tmp_path)
    for name in ("meta.json", "events.jsonl", "signals.json"):
        assert (tmp_path / name).read_bytes() == (SAMPLE / name).read_bytes(), f"{name} differs: rerun make_sample.py"
    # gzip bytes can differ between zlib builds, so compare what is inside
    new, old = (gzip.decompress((d / "ticks.json.gz").read_bytes()) for d in (tmp_path, SAMPLE))
    assert hashlib.sha256(new).hexdigest() == hashlib.sha256(old).hexdigest(), "ticks differ: rerun make_sample.py"
