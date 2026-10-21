# OWNER: B (Nikolay). Contract test for the match format (contracts/README.md), moved here from contracts/b/.
# Every check runs on both bundles: B's hand-written 90 s sample and the real judge cut that Stage 1 builds.
#     pip install -e "pipeline[dev]"   then   pytest   (from pipeline/)
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import math
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "contracts" / "b" / "sample"
JUDGE = ROOT / "web" / "public" / "replay" / "v1" / "judge"
BUNDLES = {"sample": SAMPLE, "judge": JUDGE}
HALF_L, HALF_W, GOAL_HALF_W = 52.5, 34.0, 3.66
MAX_BALL_MS = 40.0       # m/s = 144 km/h: our sanity cap for the ball, not a cited figure
MAX_PLAYER_MS = 10.3     # m/s = 37.1 km/h, the fastest top speed cited in file 19 (premierleague.com, Mar 2025)
# How close an on-ball event's player is to the ball at that moment. The sample is placed by hand; the judge cut
# comes from the file 19 movement model, which steers players there (realism report gives the real spread).
TOUCH = {"sample": dict(max=1.5), "judge": dict(median=2.0, p90=4.0)}


class Bundle:
    def __init__(self, name: str):
        d = BUNDLES[name]
        self.name, self.dir = name, d
        self.meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        self.lines = [json.loads(s) for s in (d / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.events = [ln["event"] for ln in self.lines]
        self.signals = json.loads((d / "signals.json").read_text(encoding="utf-8"))
        self.ticks = json.loads(gzip.decompress((d / "ticks.json.gz").read_bytes()))
        self.start = datetime.fromisoformat(self.meta["periods"][0]["start_time"])
        self.cut = self.meta["judge_cut"]

    def t_of(self, iso: str) -> float:
        return (datetime.fromisoformat(iso) - self.start).total_seconds()

    def ball_at(self, t: float):
        b = self.ticks["ball"]
        return b["rows"][round((t - self.ticks["t0"]) * b["hz"])]

    def player_at(self, pid: str, t: float):
        p = self.ticks["players"]
        j, k = p["ids"].index(pid), round((t - self.ticks["t0"]) * p["hz"])
        return p["rows"][k][2 * j], p["rows"][k][2 * j + 1]

    def side_of(self, team_id: str) -> str:
        return next(s for s, t in self.meta["teams"].items() if t["id"] == team_id)


_CACHE: dict = {}


@pytest.fixture(params=list(BUNDLES), scope="module")
def b(request) -> Bundle:
    if request.param not in _CACHE:
        _CACHE[request.param] = Bundle(request.param)
    return _CACHE[request.param]


def on_pitch(x, y):
    return abs(x) <= HALF_L and abs(y) <= HALF_W


def in_goal(x, y):            # behind the goal line, inside the goal mouth (net depth ~2 m)
    return HALF_L < abs(x) <= HALF_L + 2.0 and abs(y) <= GOAL_HALF_W


# ---------------------------------------------------------------- CDF
def test_events_are_valid_cdf_extreme(b):
    cdf = pytest.importorskip("cdf", reason='pip install -e "pipeline[dev]"')
    assert cdf.VERSION == b.meta["cdf_version"] == "0.3.2"
    # extreme = unknown keys fail too, so none of our extras can sneak into the CDF lines (file 26 §2)
    cdf.EventSchemaValidator().validate_schema(sample=str(b.dir / "events.jsonl"), mode="extreme", limit=None)


def test_ids_agree_across_files(b):
    roster = {p["id"]: side for side, t in b.meta["teams"].items() for p in t["players"]}
    officials = {o["id"] for o in b.meta.get("officials", [])}
    assert len({e["id"] for e in b.events}) == len(b.events)
    ids = {e["id"] for e in b.events}
    for ln in b.lines:
        e = ln["event"]
        assert ln["match"]["id"] == b.meta["match"]["id"]
        if e["type"] == "referee":
            assert e["official_id"] in officials and "player_id" not in e
        else:
            assert roster[e["player_id"]] == b.side_of(e["team_id"])         # the validator skips this (file 26)
        if e["receiver_id"] is not None:
            assert roster[e["receiver_id"]] == b.side_of(e["receiver_team_id"])
        assert all(r in ids for r in e["related_event_ids"] or [])
    assert b.signals["match_id"] == b.ticks["match_id"] == b.meta["match"]["id"]
    assert b.ticks["players"]["ids"] == [p["id"] for s in ("home", "away") for p in b.meta["teams"][s]["players"]]
    numbers = [(s, p["jersey_number"]) for s, t in b.meta["teams"].items() for p in t["players"]]
    assert len(set(numbers)) == len(numbers)


# ---------------------------------------------------------------- signals
def test_every_event_has_matching_signals(b):
    sig = b.signals["events"]
    assert list(sig) == [e["id"] for e in b.events]                             # same ids, same order
    for e in b.events:
        s = sig[e["id"]]
        assert s["t"] == pytest.approx(b.t_of(e["time"]), abs=1e-6)
        assert s["reveal_t"] >= s["t"]
        if e["receiver_time"]:
            assert s["reveal_t"] == pytest.approx(b.t_of(e["receiver_time"]), abs=1e-6)
        assert (0 < s["xg"] < 1) if e["type"] == "shot" else s["xg"] is None
        assert s["priority"] in (0, 1, 2, 3)
        assert s["zone"]["third"] in ("defensive_third", "middle_third", "attacking_third")
        assert s["zone"]["side"] in ("near", "centre", "far")
        assert isinstance(s["zone"]["in_box"], bool) and s["zone"]["words"]
        assert s["spoken"].strip() and s["spoken_past"].strip()


def test_per_second_signals_cover_the_window_in_range(b):
    rows = b.signals["per_second"]
    assert b.signals["hz"] == 1
    assert [r["t"] for r in rows] == list(range(int(b.cut["t_start"]), int(b.cut["t_end"]) + 1))
    for r in rows:
        assert sum(r["win_prob"].values()) == pytest.approx(1.0, abs=0.002)
        assert r["suspense"] >= 0 and 0 <= r["tension"] <= 1
        assert all(0 <= v <= 1 for v in r["danger"].values())
        for end in ("H", "A"):
            c = r["crowd"][end]
            assert 0 <= c["excitement"] <= 1 and -1 <= c["valence"] <= 1 and -1 <= c["danger"] <= 1
    for o in b.signals["crowd_one_shots"]:
        assert o["end"] in ("H", "A") and b.cut["t_start"] <= o["t"] <= b.cut["t_end"]


# ---------------------------------------------------------------- ticks
def test_ticks_cover_the_full_window_at_the_right_rates(b):
    dur = b.cut["t_end"] - b.cut["t_start"]
    assert b.ticks["t0"] == b.cut["t_start"] and b.ticks["duration_s"] == dur
    ball, players = b.ticks["ball"], b.ticks["players"]
    assert ball["hz"] == b.meta["rates"]["ball_hz"] == 25
    assert players["hz"] == b.meta["rates"]["player_hz"] and players["hz"] >= 1       # where_is needs >= 1 Hz
    assert len(ball["rows"]) == round(dur * ball["hz"]) + 1                          # both ends included
    assert len(players["rows"]) == round(dur * players["hz"]) + 1
    assert ball["columns"] == ["x", "y", "z", "alive", "poss"]
    assert all(len(r) == 5 and r[3] in (0, 1) and r[4] in ("home", "away", None) for r in ball["rows"])
    assert all((r[4] is not None) == (r[3] == 1) for r in ball["rows"])               # live ball <=> someone has it
    assert all(len(r) == 2 * len(players["ids"]) for r in players["rows"])


# ---------------------------------------------------------------- time order
def test_timestamps_are_in_order_and_utc(b):
    times = [b.t_of(e["time"]) for e in b.events]
    assert times == sorted(times)
    clock0 = b.meta["periods"][0]["clock_start"]
    offset = int(clock0[:2]) * 60
    for e in b.events:
        assert e["time"].endswith("Z")                                               # file 26: UTC only
        cs = round((b.t_of(e["time"]) + offset) * 100)
        assert e["match_clock"] == f"{cs // 6000:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"
        if e["receiver_time"]:
            assert b.t_of(e["receiver_time"]) > b.t_of(e["time"])
    assert b.cut["t_start"] <= times[0] and times[-1] <= b.cut["t_end"]


# ---------------------------------------------------------------- positions and motion
def test_positions_stay_on_the_pitch(b):
    for e in b.events:
        assert on_pitch(e["x"], e["y"]), e["id"]
        if e["x_end"] is not None:
            assert on_pitch(e["x_end"], e["y_end"]) or (e["type"] == "shot" and in_goal(e["x_end"], e["y_end"]))
    for x, y, z, alive, _ in b.ticks["ball"]["rows"]:
        assert on_pitch(x, y) or in_goal(x, y)                                       # in the net after a goal
        assert 0.0 < z <= 15.0
    for r in b.ticks["players"]["rows"]:
        assert all(on_pitch(r[i], r[i + 1]) for i in range(0, len(r), 2))


def test_speeds_are_realistic(b):
    rows, hz = b.ticks["ball"]["rows"], b.ticks["ball"]["hz"]
    vb = max(math.hypot(q[0] - p[0], q[1] - p[1]) * hz for p, q in zip(rows, rows[1:]))
    assert 5.0 < vb <= MAX_BALL_MS
    p = b.ticks["players"]
    for j, pid in enumerate(p["ids"]):
        v = max(math.hypot(q[2 * j] - a[2 * j], q[2 * j + 1] - a[2 * j + 1]) * p["hz"]
                for a, q in zip(p["rows"], p["rows"][1:]))
        assert v <= MAX_PLAYER_MS, f"{pid} runs at {v:.1f} m/s"


def test_events_line_up_with_the_ball_and_players(b):
    dists = []
    for e in b.events:
        t = b.t_of(e["time"])
        bx, by = b.ball_at(t)[:2]
        if e["type"] != "referee":          # a VAR check is placed at the incident it reviews, not at the ball
            assert math.hypot(bx - e["x"], by - e["y"]) < 0.05, e["id"]               # ball is where the event says
            px, py = b.player_at(e["player_id"], t)                                  # nearest 5 Hz row (<= 0.1 s)
            dists.append(math.hypot(px - e["x"], py - e["y"]))
        if e["receiver_time"]:
            rx, ry = b.ball_at(b.t_of(e["receiver_time"]))[:2]
            assert math.hypot(rx - e["x_end"], ry - e["y_end"]) < 0.05, e["id"]
    dists.sort()
    lim = TOUCH[b.name]
    if "max" in lim:
        assert dists[-1] <= lim["max"]
    else:
        assert dists[len(dists) // 2] <= lim["median"] and dists[int(0.9 * (len(dists) - 1))] <= lim["p90"]


# ---------------------------------------------------------------- the story
def test_bundle_tells_the_required_story(b):
    types = [(e["type"], e["sub_type"], e["outcome_type"], e.get("team_id")) for e in b.events]
    run = best = 0
    for prev, cur in zip([None] + types, types):
        ok = cur[0] == "pass" and cur[2] == "successful"
        run = run + 1 if ok and prev and prev[0] == "pass" and prev[3] == cur[3] and prev[2] == "successful" else int(ok)
        best = max(best, run)
    assert best >= 3, "pass chain"
    shots = [t for t in types if t[0] == "shot"]
    assert any(t[0] == "goalkeeping" and t[1] == "save" for t in types), "save"
    goals = [e for e in b.events if e["type"] == "shot" and e["outcome_type"] == "successful"]
    assert goals, "goal"
    if b.name == "judge":                       # BUILD_PLAN Stage 1: >= 1 goal, save, card, VAR-style check, 4 shots
        assert len(shots) >= 4
        assert any(t[2] in ("yellow_card", "red_card") for t in types), "card"
        assert any(t[0] == "referee" and t[1] == "var_check" for t in types), "var_check"
    g = goals[0]
    side = b.side_of(g["team_id"])
    reveal = b.signals["events"][g["id"]]["reveal_t"]
    rows = b.signals["per_second"]
    start = b.cut.get("score_at_start", {"home": 0, "away": 0})[side]
    before, after = [r for r in rows if r["t"] < reveal], [r for r in rows if r["t"] >= reveal]
    assert all(r["score"][side] == start for r in before)                           # no score leak before the goal
    assert after[0]["score"][side] == start + 1
    assert after[0]["win_prob"][side] > before[-1]["win_prob"][side] + 0.1


# ---------------------------------------------------------------- determinism (sample; the judge cut: test_stage1)
def test_regenerating_the_sample_gives_identical_files(tmp_path):
    spec = importlib.util.spec_from_file_location("make_sample", ROOT / "contracts" / "b" / "make_sample.py")
    ms = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ms)
    ms.write(tmp_path)
    for name in ("meta.json", "events.jsonl", "signals.json"):
        assert (tmp_path / name).read_bytes() == (SAMPLE / name).read_bytes(), f"{name} differs: rerun make_sample.py"
    new, old = (gzip.decompress((d / "ticks.json.gz").read_bytes()) for d in (tmp_path, SAMPLE))
    assert hashlib.sha256(new).hexdigest() == hashlib.sha256(old).hexdigest(), "ticks differ: rerun make_sample.py"
