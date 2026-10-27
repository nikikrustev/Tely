"""Write the hand-written 90 s sample match for docs/match-format.md (match format v0.1.0).

    python pipeline/sample_match/make_sample.py              # writes pipeline/sample_match/sample/
    python pipeline/sample_match/make_sample.py --out DIR    # writes somewhere else (the test uses this)

The story is written by hand in SCRIPT below: a Reds pass chain from kick-off, a shot saved by the
Navy keeper, a Navy spell of possession, an interception, a Reds counter, a cross and a headed goal.
Everything else (ball flight, 22 player tracks, signals) is computed from SCRIPT with fixed formulas.
Standard library only and no randomness, so every run writes byte-identical files.

All clubs, players and the venue are fictional. Nothing here comes from real match data.
The per-second signals use simple sample-only versions of the file 23/38/39 formulas; Stage 1
(pipeline/tely/interpret.py, crowd.py) replaces them but must keep this file format.
The format itself is documented field by field in docs/match-format.md.
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

FORMAT_VERSION = "0.1.0"
CDF_VERSION = "0.3.2"            # file 26: the version common-data-format-validator 0.1.1 checks
MATCH_ID = "syn_sample_0001"
KICKOFF = datetime(2026, 10, 24, 15, 0, 0, tzinfo=timezone.utc)
PERIOD = "first_half"
DURATION_S = 90
BALL_HZ = 25                     # ball rows per second (one every 40 ms, CDF tracking rate)
PLAYER_HZ = 5                    # player rows per second (why 5 Hz: docs/match-format.md, ticks.json.gz)
HALF_L, HALF_W = 52.5, 34.0      # pitch is 105 x 68 m, origin at the centre spot
GOAL_HALF_W = 3.66               # half the goal mouth (7.32 m)
BALL_Z = 0.11                    # ball centre height when it is on the grass (m)
HANDS_Z = 1.0                    # ball height when a keeper holds it (m)

TEAMS = {
    "home": dict(id="syn_reds", name="Ember Vale FC", short_name="Reds", formation="4-3-3",
                 attacks="+x", kit=dict(shirt="red", sleeves="red", shorts="white", socks="red",
                                        words="red shirts, white shorts")),
    "away": dict(id="syn_navy", name="Port Halden FC", short_name="Navy", formation="4-4-2",
                 attacks="-x", kit=dict(shirt="navy", sleeves="sky blue", shorts="navy", socks="navy",
                                        words="navy shirts with sky-blue sleeves")),
}
DIR = {"home": +1, "away": -1}   # +1 = attacks towards +x (CDF: home attacks left to right all match)

# (id, first name, last name, shirt, position, line, base x, base y). Base = the player's spot when the
# ball is on the centre spot and nobody has it. Names are invented; any match with a real person is chance.
PLAYERS = {
    "home": [
        ("r1", "Bram", "Velkov", 1, "GK", "gk", -49.0, 0.0),
        ("r2", "Teo", "Lindgaard", 2, "RB", "def", -30.0, -22.0),
        ("r5", "Dario", "Fenwick", 5, "CB", "def", -34.0, -8.0),
        ("r4", "Luka", "Moravec", 4, "CB", "def", -34.0, 8.0),
        ("r3", "Kofi", "Ashdown", 3, "LB", "def", -30.0, 22.0),
        ("r6", "Ruben", "Haldane", 6, "DM", "mid", -20.0, 0.0),
        ("r8", "Milo", "Petrakis", 8, "CM", "mid", -12.0, -10.0),
        ("r10", "Jonas", "Ilievski", 10, "AM", "mid", -10.0, 10.0),
        ("r7", "Andre", "Wexford", 7, "RW", "fwd", -2.0, -24.0),
        ("r9", "Caleb", "Ndiaye-Ross", 9, "ST", "fwd", -1.0, 0.0),
        ("r11", "Yusuf", "Brennock", 11, "LW", "fwd", -2.0, 24.0),
    ],
    "away": [
        ("n1", "Henrik", "Solvang", 1, "GK", "gk", 49.0, 0.0),
        ("n2", "Paolo", "Sandrelli", 2, "RB", "def", 30.0, 22.0),
        ("n5", "Tobias", "Kwartey", 5, "CB", "def", 34.0, 8.0),
        ("n4", "Mateo", "Strandberg", 4, "CB", "def", 34.0, -8.0),
        ("n3", "Aiden", "Farrow", 3, "LB", "def", 30.0, -22.0),
        ("n7", "Kasim", "Dorrell", 7, "RM", "mid", 16.0, 24.0),
        ("n6", "Felix", "Arnaud", 6, "CM", "mid", 16.0, 7.0),
        ("n8", "Rafael", "Quist", 8, "CM", "mid", 16.0, -7.0),
        ("n11", "Owen", "Tadesse", 11, "LM", "mid", 16.0, -24.0),
        ("n9", "Viktor", "Hale", 9, "ST", "fwd", 9.5, 5.0),
        ("n10", "Bastian", "Oduya", 10, "ST", "fwd", 9.5, -5.0),
    ],
}

# The match, by hand. t = seconds since kick-off (None = the moment the previous ball arrives).
# at = where the player touches the ball, end = where it arrives, v = average ball speed (m/s).
# A pass's receiver must make the next touch, so every gap between two actions is a carry.
SCRIPT = [
    dict(t=0.00, act="pass", p="r9", at=(0.0, 0.0), to="r8", end=(-8.0, -4.0), v=10, sub="kick_off"),
    dict(t=2.40, act="pass", p="r8", at=(-9.0, -6.0), to="r5", end=(-28.0, -10.0), v=15),
    dict(t=5.20, act="pass", p="r5", at=(-27.0, -8.0), to="r4", end=(-28.0, 10.0), v=13),
    dict(t=8.40, act="pass", p="r4", at=(-24.0, 12.0), to="r3", end=(-14.0, 27.0), v=14, body="left_foot"),
    dict(t=11.60, act="pass", p="r3", at=(-8.0, 28.0), to="r10", end=(2.0, 16.0), v=13, body="left_foot"),
    dict(t=14.40, act="pass", p="r10", at=(6.0, 14.0), to="r6", end=(-6.0, 3.0), v=13),
    dict(t=16.80, act="pass", p="r6", at=(-4.0, 2.0), to="r8", end=(4.0, -12.0), v=14),
    dict(t=20.00, act="pass", p="r8", at=(10.0, -11.0), to="r10", end=(14.0, 6.0), v=15),
    dict(t=22.40, act="pass", p="r10", at=(18.0, 5.0), to="r9", end=(24.0, 0.0), v=12),
    dict(t=23.60, act="pass", p="r9", at=(24.0, 0.5), to="r10", end=(29.0, 4.0), v=10),
    dict(t=25.20, act="shot", p="r10", at=(33.0, 2.0), end=(51.2, -1.4), v=27, outcome="saved", keeper="n1",
         xg=0.09),
    dict(t=31.00, act="pass", p="n1", at=(46.0, -6.0), to="n4", end=(36.0, -15.0), v=10, body="hands"),
    dict(t=34.00, act="pass", p="n4", at=(33.0, -14.0), to="n5", end=(34.0, 10.0), v=15, body="left_foot"),
    dict(t=37.20, act="pass", p="n5", at=(30.0, 12.0), to="n2", end=(22.0, 27.0), v=14),
    dict(t=40.80, act="pass", p="n2", at=(14.0, 28.0), to="n7", end=(2.0, 24.0), v=13),
    dict(t=44.00, act="pass", p="n7", at=(-6.0, 22.0), to="n6", end=(-2.0, 6.0), v=14),
    dict(t=47.20, act="pass", p="n6", at=(-6.0, 4.0), to="n10", end=(-14.0, -6.0), v=13),
    dict(t=50.00, act="pass", p="n10", at=(-18.0, -8.0), to="n9", end=(-26.0, -5.3), v=15, cut_by="r5"),
    dict(t=51.80, act="pass", p="r5", at=(-22.0, -4.0), to="r10", end=(-6.0, 10.0), v=17),
    dict(t=55.20, act="pass", p="r10", at=(6.0, 7.0), to="r7", end=(26.0, -20.0), v=19),
    dict(t=59.40, act="pass", p="r7", at=(38.0, -24.0), to="r9", end=(46.0, 1.5), v=18, loft=3.0, z_end=1.9),
    dict(t=None, act="shot", p="r9", at=(46.0, 1.5), end=(52.5, 2.6), v=16, outcome="goal", xg=0.31,
         body="head", z0=1.9, z_end=0.6, net=(54.0, 2.8)),
]

# Off-ball runs: (t, player, x, y). The shooter jogs back; on the counter the striker stays high and the
# winger and striker sprint in behind; after the goal come the celebration, the walk back and the restart.
RUNS = [
    (28.00, "r10", 30.0, 4.0), (34.00, "r10", 16.0, 8.0),
    (50.00, "r9", 2.0, -2.0), (54.00, "r9", 20.0, -4.0), (58.00, "r9", 36.0, -1.0),
    (53.00, "r7", 10.0, -23.0),
    (61.20, "n1", 51.6, 2.0), (66.40, "n1", 51.4, 2.4), (68.00, "n1", 49.0, 0.0),
    (66.00, "r9", 50.0, -31.0), (78.00, "r9", 24.0, -14.0), (88.00, "r9", 2.0, -4.0),
    (66.40, "r7", 48.5, -29.5), (78.00, "r7", 22.0, -20.0), (88.00, "r7", 0.0, -19.0),
    (67.20, "r10", 47.5, -28.5), (79.00, "r10", 15.0, -5.0), (89.00, "r10", -8.0, 8.0),
    (84.00, "n9", 0.6, 0.4), (90.00, "n9", 0.6, 0.4),
    (84.00, "n10", 1.2, -2.0), (90.00, "n10", 1.2, -2.0),
]
# Dead-ball path after the goal: (t, x, y, z). The keeper fetches it and kicks it back to the centre spot.
DEAD_BALL = [(66.00, 54.0, 2.8, BALL_Z), (66.40, 51.4, 2.4, HANDS_Z), (68.00, 49.0, 0.0, HANDS_Z)]
DEAD_KICK = dict(t0=68.00, t1=71.00, start=(49.0, 0.0), end=(4.0, 0.0), z0=HANDS_Z, loft=8.0)
DEAD_ROLL = dict(t0=71.00, t1=74.00, end=(0.0, 0.0))


# ---------------------------------------------------------------- helpers
def frame(t: float) -> int:
    return round(t * BALL_HZ)


def iso(f: int) -> str:
    """Ball frame -> CDF UTC time with milliseconds, e.g. 2026-10-24T15:00:25.200Z."""
    d = KICKOFF + timedelta(milliseconds=f * 1000 // BALL_HZ)
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + f"{d.microsecond // 1000:03d}Z"


def match_clock(f: int) -> str:
    """Ball frame -> CDF match clock "MM:SS.mm" (minutes, seconds, hundredths)."""
    cs = f * 100 // BALL_HZ
    return f"{cs // 6000:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def dist(a, b) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def lerp(a: float, b: float, u: float) -> float:
    return a + (b - a) * u


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def r2(v: float) -> float:
    return round(v + 0.0, 2)   # + 0.0 turns -0.0 into 0.0


ROSTER = {p[0]: dict(side=side, first=p[1], last=p[2], number=p[3], position=p[4], line=p[5],
                     base=(p[6], p[7])) for side, ps in PLAYERS.items() for p in ps}
PLAYER_IDS = [p[0] for side in ("home", "away") for p in PLAYERS[side]]


def team_word(side: str) -> str:
    return TEAMS[side]["short_name"]


def name(pid: str) -> str:
    return ROSTER[pid]["last"]


def zone(x: float, y: float, side: str) -> dict:
    """Ball-first zone words (file 36): third from the acting team's view, side is absolute.
    near = the main-stand touchline (y < 0 in CDF, y runs bottom to top), far = the opposite one."""
    ax = x * DIR[side]                       # + = towards the goal this team attacks
    third = "defensive_third" if ax < -17.5 else "middle_third" if ax < 17.5 else "attacking_third"
    s = "near" if y < -11.33 else "far" if y > 11.33 else "centre"
    in_box = ax > HALF_L - 16.5 and abs(y) < 20.16
    words = {"defensive_third": "defensive third", "middle_third": "midfield",
             "attacking_third": "attacking third"}[third]
    words += ", " + {"near": "near side", "far": "far side", "centre": "centre"}[s]
    return dict(third=third, side=s, in_box=in_box, words=words)


# ---------------------------------------------------------------- 1. events + ball path from SCRIPT
def build_script():
    """Returns (actions, ball_segments, anchors).
    actions: on-ball moments in time order, as dicts used to write CDF lines and signals.
    ball_segments: contiguous pieces of the ball path (f0, f1, start, end, kind, extra).
    anchors: {player_id: [(frame, x, y)]} where a player must be at a given moment."""
    actions, segs, anchors = [], [], {pid: [] for pid in PLAYER_IDS}
    goal_frame = None
    prev_arrival = None
    for i, s in enumerate(SCRIPT):
        f0 = prev_arrival[0] if s["t"] is None else frame(s["t"])
        if prev_arrival is not None:
            fa, pa, holder, z_hold = prev_arrival
            assert holder == s["p"], f"step {i}: {s['p']} plays the ball but {holder} has it"
            if f0 > fa:          # carry (or a keeper walking with the ball in their hands)
                segs.append((fa, f0, pa, s["at"], "carry", dict(z0=z_hold, z1=z_hold, side=ROSTER[holder]["side"])))
            else:
                assert f0 == fa and pa == s["at"], f"step {i}: first-time touch must be where the ball arrived"
        side = ROSTER[s["p"]]["side"]
        f1 = f0 + max(1, round(dist(s["at"], s["end"]) / s["v"] * BALL_HZ))
        anchors[s["p"]].append((f0, *s["at"]))
        z0 = s.get("z0", BALL_Z if s.get("body") != "hands" else HANDS_Z)
        segs.append((f0, f1, s["at"], s["end"], "flight",
                     dict(z0=z0, z1=s.get("z_end", BALL_Z), loft=s.get("loft", 0.0), side=side)))
        act = dict(kind=s["act"], f=f0, f_end=f1, player=s["p"], side=side, at=s["at"], end=s["end"],
                   body=s.get("body", "right_foot"), sub=s.get("sub"))
        actions.append(act)
        if s["act"] == "pass":
            if "cut_by" in s:
                act.update(outcome="intercepted", receiver=None)
                actions.append(dict(kind="interception", f=f1, f_end=f1, player=s["cut_by"],
                                    side=ROSTER[s["cut_by"]]["side"], at=s["end"], end=None, body="right_foot",
                                    sub="interception", related=act))
                anchors[s["cut_by"]].append((f1, *s["end"]))
                prev_arrival = (f1, s["end"], s["cut_by"], BALL_Z)
            else:
                act.update(outcome="successful", receiver=s["to"])
                anchors[s["to"]].append((f1, *s["end"]))
                prev_arrival = (f1, s["end"], s["to"], s.get("z_end", BALL_Z))
        else:  # shot
            act.update(outcome=s["outcome"], xg=s["xg"])
            if s["outcome"] == "saved":
                actions.append(dict(kind="save", f=f1, f_end=f1, player=s["keeper"],
                                    side=ROSTER[s["keeper"]]["side"], at=s["end"], end=None, body="hands",
                                    sub="save", related=act))
                anchors[s["keeper"]].append((f1, *s["end"]))
                prev_arrival = (f1, s["end"], s["keeper"], HANDS_Z)
            else:   # goal: the ball crosses the line at f1, then nestles in the net and is dead
                goal_frame = f1
                fn = f1 + 5
                segs.append((f1, fn, s["end"], s["net"], "net", dict(z0=s["z_end"], z1=BALL_Z, side=side)))
                prev_arrival = None
                last_f, last_p = fn, s["net"]
    # dead ball after the goal
    pts = [(frame(t), (x, y), z) for t, x, y, z in DEAD_BALL]
    f_prev, p_prev, z_prev = last_f, last_p, BALL_Z
    for f, p, z in pts:
        segs.append((f_prev, f, p_prev, p, "dead", dict(z0=z_prev, z1=z, side=None)))
        f_prev, p_prev, z_prev = f, p, z
    k = DEAD_KICK
    segs.append((frame(k["t0"]), frame(k["t1"]), k["start"], k["end"], "dead",
                 dict(z0=k["z0"], z1=BALL_Z, loft=k["loft"], side=None, ease=True)))
    r = DEAD_ROLL
    segs.append((frame(r["t0"]), frame(r["t1"]), k["end"], r["end"], "dead", dict(z0=BALL_Z, z1=BALL_Z, side=None,
                                                                                     ease=True)))
    segs.append((frame(r["t1"]), DURATION_S * BALL_HZ, r["end"], r["end"], "dead", dict(z0=BALL_Z, z1=BALL_Z,
                                                                                         side=None)))
    for t, pid, x, y in RUNS:
        anchors[pid].append((frame(t), x, y))
    for pid in anchors:
        anchors[pid].sort()
    actions.sort(key=lambda a: a["f"])          # stable: a save/interception stays after its shot/pass
    return actions, segs, anchors, goal_frame


def ball_track(segs, goal_frame):
    """25 Hz rows [x, y, z, alive, poss]. Flights slow down a little (grass friction): the ball leaves the
    foot at 1.3x and arrives at 0.7x the average speed. Lofted balls follow a parabola."""
    n = DURATION_S * BALL_HZ + 1
    rows = [None] * n
    for f0, f1, a, b, kind, ex in segs:
        for f in range(f0, min(f1, n - 1) + 1):
            u = (f - f0) / (f1 - f0) if f1 > f0 else 1.0
            if kind == "flight" or kind == "net" or ex.get("ease"):
                pos = u * (1.3 - 0.3 * u)
            else:
                pos = u
            x, y = lerp(a[0], b[0], pos), lerp(a[1], b[1], pos)
            z = lerp(ex["z0"], ex["z1"], u) + 4 * ex.get("loft", 0.0) * u * (1 - u)
            alive = goal_frame is None or f <= goal_frame
            side = ex["side"] if alive else None
            rows[f] = [r2(x), r2(y), r2(z), 1 if alive else 0, side]
    assert all(r is not None for r in rows), "ball path has a gap"
    return rows


# ---------------------------------------------------------------- 2. players
LINE_K = {"def": 0.25, "mid": 0.40, "fwd": 0.35}        # how far a line follows the ball along x
LINE_PUSH = {"def": 6.0, "mid": 8.0, "fwd": 10.0}     # metres a line steps up when its team has the ball
DROP = 2.0                                               # metres a line drops when the other team has it


def formation_tracks(ball):
    """Team shape at every ball frame: each player's base spot shifted towards the (smoothed) ball, pushed up
    when their team has the ball. Smoothing (4 s for both the ball and possession) keeps runs at human speed."""
    bx = by = 0.0
    ps = 0.0                                             # +1 home has the ball, -1 away, 0 nobody
    a_ball, a_poss = 1 - math.exp(-1 / (4.0 * BALL_HZ)), 1 - math.exp(-1 / (4.0 * BALL_HZ))
    out = {pid: [] for pid in PLAYER_IDS}
    for row in ball:
        x, y, _, alive, side = row
        bx += a_ball * (x - bx)
        by += a_ball * (y - by)
        target = 0.0 if side is None else (1.0 if side == "home" else -1.0)
        ps += a_poss * (target - ps)
        for pid in PLAYER_IDS:
            p = ROSTER[pid]
            d = DIR[p["side"]]
            if p["line"] == "gk":
                gx = p["base"][0] + d * 0.07 * (d * bx + HALF_L)    # steps off the line as play moves away
                gy = 0.12 * by
            else:
                own = ps * d                                         # + when this player's team has the ball
                gx = p["base"][0] + LINE_K[p["line"]] * bx + d * (LINE_PUSH[p["line"]] * max(own, 0.0)
                                                                   - DROP * max(-own, 0.0))
                gy = 0.8 * p["base"][1] + 0.3 * by
            out[pid].append((max(-HALF_L + 1, min(HALF_L - 1, gx)), max(-HALF_W + 1, min(HALF_W - 1, gy))))
    return out


def player_tracks(ball, anchors):
    """Players at PLAYER_HZ. Each player follows their formation spot, bent so that they are exactly at each
    anchor (a touch, a reception, a run) at its moment:
      - anchors <= 6 s apart: straight line between them (a carry stays glued to the ball);
      - 6-12 s apart: the offset from the formation spot slides from one anchor's to the next;
      - further apart, or before the first / after the last: the offset fades out over 4 s."""
    form = formation_tracks(ball)
    step = BALL_HZ // PLAYER_HZ
    frames = list(range(0, DURATION_S * BALL_HZ + 1, step))
    rows = [[] for _ in frames]
    fade = 4.0 * BALL_HZ
    for pid in PLAYER_IDS:
        fm, an = form[pid], anchors[pid]
        offs = [(f, x - fm[f][0], y - fm[f][1], x, y) for f, x, y in an]
        for k, f in enumerate(frames):
            fx, fy = fm[f]
            prev = next((o for o in reversed(offs) if o[0] <= f), None)
            nxt = next((o for o in offs if o[0] > f), None)
            if prev and nxt and nxt[0] - prev[0] <= 6 * BALL_HZ:
                u = (f - prev[0]) / (nxt[0] - prev[0])
                x, y = lerp(prev[3], nxt[3], u), lerp(prev[4], nxt[4], u)
            elif prev and nxt and nxt[0] - prev[0] <= 12 * BALL_HZ:
                u = smoothstep((f - prev[0]) / (nxt[0] - prev[0]))
                x, y = fx + lerp(prev[1], nxt[1], u), fy + lerp(prev[2], nxt[2], u)
            else:
                ox = oy = 0.0
                for o in (prev, nxt):
                    if o:
                        w = smoothstep(1 - abs(f - o[0]) / fade)
                        ox, oy = ox + o[1] * w, oy + o[2] * w
                x, y = fx + ox, fy + oy
            rows[k] += [r2(x), r2(y)]
    return rows


# ---------------------------------------------------------------- 3. CDF event lines
def cdf_lines(actions):
    for i, a in enumerate(actions):
        a["id"] = f"e{i + 1:04d}"
    lines = []
    for a in actions:
        team_id = TEAMS[a["side"]]["id"]
        ev = {"id": a["id"], "time": iso(a["f"]), "period": PERIOD, "type": None, "sub_type": None,
              "is_successful": True, "outcome_type": "successful", "player_id": a["player"], "team_id": team_id,
              "receiver_id": None, "receiver_time": None, "receiver_team_id": None,
              "x": r2(a["at"][0]), "y": r2(a["at"][1]), "x_end": None, "y_end": None,
              "body_part": a["body"], "related_event_ids": None, "match_clock": match_clock(a["f"])}
        if a["kind"] == "pass":
            ev.update(type="pass", sub_type=a["sub"], x_end=r2(a["end"][0]), y_end=r2(a["end"][1]))
            if a["outcome"] == "successful":
                ev.update(receiver_id=a["receiver"], receiver_time=iso(a["f_end"]), receiver_team_id=team_id)
            else:
                ev.update(is_successful=False, outcome_type=a["outcome"])
        elif a["kind"] == "shot":
            ev.update(type="shot", x_end=r2(a["end"][0]), y_end=r2(a["end"][1]))
            if a["outcome"] != "goal":
                ev.update(is_successful=False, outcome_type=a["outcome"])
        elif a["kind"] == "save":
            ev.update(type="goalkeeping", sub_type="save")
        elif a["kind"] == "interception":
            ev.update(type="defending", sub_type="interception")
        lines.append(ev)
    by_id = {a["id"]: (a, ev) for a, ev in zip(actions, lines)}
    for a, ev in zip(actions, lines):              # link pairs both ways: shot <-> save, pass <-> interception
        if "related" in a:
            rel = a["related"]["id"]
            ev["related_event_ids"] = [rel]
            by_id[rel][1]["related_event_ids"] = [a["id"]]
    for k, a in enumerate(actions):                # the goal links to the pass that set it up (the assist)
        if a["kind"] == "shot" and a["outcome"] == "goal" and k and actions[k - 1]["kind"] == "pass":
            lines[k]["related_event_ids"] = [actions[k - 1]["id"]]
    return [{"match": {"id": MATCH_ID}, "meta": {"is_synced": True}, "event": ev} for ev in lines]


# ---------------------------------------------------------------- 4. signals
LAM = {"home": 1.5, "away": 1.2}   # pre-match goal rates per 95 min (sample-only, home edge)
MATCH_S = 95 * 60
P_BASE, P_DANGER = 0.0003, 0.04    # P(goal in the next second) = P_BASE + P_DANGER * danger^2 (sample-only)
REF_SUSPENSE = 0.03                # sample-only normaliser for tension (Stage 1: p99 over ~500 matches)


def danger_of(x: float, y: float, side: str) -> float:
    """Berbata definition (sample v0): how close the team with the ball is to scoring, 0..1.
    1 - distance to the goal it attacks / 40 m, to the power 1.5. 0 beyond 40 m."""
    gx = HALF_L * DIR[side]
    return max(0.0, 1 - math.hypot(gx - x, y) / 40.0) ** 1.5


def pois(k: int, mu: float) -> float:
    return math.exp(-mu) * mu ** k / math.factorial(k)


def win_prob(gd: int, t: float):
    """File 23 Poisson grid: remaining goals for each side ~ Poisson(rate x time left). -> [home, draw, away]."""
    left = max(MATCH_S - t, 0) / MATCH_S
    mh, ma = LAM["home"] * left, LAM["away"] * left
    out = [0.0, 0.0, 0.0]
    for x in range(11):
        for y in range(11):
            d = gd + x - y
            out[0 if d > 0 else 1 if d == 0 else 2] += pois(x, mh) * pois(y, ma)
    s = sum(out)
    return [v / s for v in out]


def suspense(gd: int, t: float, ph: float, pa: float) -> float:
    """File 39: spread of next-second win-probability outcomes (Ely et al. suspense)."""
    mu, bh, ba = win_prob(gd, t), win_prob(gd + 1, t), win_prob(gd - 1, t)
    p0 = 1 - ph - pa
    b0 = [(mu[i] - ph * bh[i] - pa * ba[i]) / p0 for i in range(3)]
    sq = lambda b: sum((b[i] - mu[i]) ** 2 for i in range(3))
    return math.sqrt(ph * sq(bh) + pa * sq(ba) + p0 * sq(b0))


REACT = {  # file 38: (d_excitement, d_valence, tau_s) from the listening end's view, after the event
    ("goal", True): (1.00, 1.00, 25), ("goal", False): (0.30, -0.90, 30),
    ("shot", True): (0.55, -0.35, 5), ("shot", False): (0.25, 0.35, 4)}
ONE_SHOT = {("goal", True): "roar", ("goal", False): "stunned_hush",
            ("shot", True): "ooh_groan", ("shot", False): "relief_applause"}


def crowd_states(seconds, shots, end, lookahead_s=8.0, lead_s=5.0):
    """File 38 crowd_states for one end (H or A). shots: (t_shot, t_reveal, side, xg, is_goal).
    Look-ahead uses xG only: a goal and a miss build the same swell. Reactions start at t_reveal."""
    me = "home" if end == "H" else "away"
    out, exc_s, val_s, dang_s = [], 0.15, 0.0, 0.0
    up, dn = 1 - math.exp(-1 / 0.8), 1 - math.exp(-1 / 4.0)
    for row in seconds:
        t = row["t"]
        mine = 0.0 if row["poss"] is None else (1.0 if row["poss"] == me else -1.0)
        threat = row["danger"][row["poss"]] if row["poss"] else 0.0
        danger = mine * threat
        antic = sum((1 if side == me else -1) * min(1.0, 2 * xg) * smoothstep(1 - (ts - t) / lead_s)
                    for ts, _, side, xg, _ in shots if t < ts <= t + lookahead_s)
        de = dv = 0.0
        for _, tr, side, _, goal in shots:
            if tr <= t:
                d_e, d_v, tau = REACT[("goal" if goal else "shot", side == me)]
                w = math.exp(-(t - tr) / tau)
                de, dv = de + d_e * w, dv + d_v * w
        diff = (row["score"]["home"] - row["score"]["away"]) * (1 if end == "H" else -1)
        exc = max(0.0, min(1.0, 0.15 + 0.35 * abs(danger) + 0.5 * abs(antic) + de))
        val = max(-1.0, min(1.0, 0.5 * math.tanh(0.5 * diff) + 0.4 * danger + 0.3 * antic + dv))
        exc_s += (up if exc > exc_s else dn) * (exc - exc_s)
        val_s += (1 - math.exp(-1 / 2.0)) * (val - val_s)
        dang_s += (1 - math.exp(-1 / 1.5)) * (danger + 0.5 * antic - dang_s)
        out.append(dict(excitement=r2(exc_s), valence=r2(val_s), danger=r2(max(-1.0, min(1.0, dang_s)))))
    return out


def spoken_lines(a, actions):
    """Present-tense line (spoken, for 'what just happened') and a past-tense fragment (spoken_past, for
    'while we talked, ...'). Ball-first grammar from file 36: where, which team, then who."""
    team, who = team_word(a["side"]), name(a["player"])
    where = zone(*a["at"], a["side"])["words"]
    where = where[0].upper() + where[1:]
    if a["kind"] == "pass" and a["sub"] == "kick_off":
        rec = name(a["receiver"])
        return (f"Kick-off. {team} get us under way, {who} to {rec}.", f"{team} kicked off")
    if a["kind"] == "pass" and a["outcome"] == "successful":
        rec = name(a["receiver"])
        if zone(*a["end"], a["side"])["in_box"] and zone(*a["at"], a["side"])["side"] != "centre":
            return (f"{where}, {team}. {who} crosses for {rec}.", f"{who} crossed for {rec}")
        return (f"{where}, {team}. {who} to {rec}.", f"{who} found {rec}")
    if a["kind"] == "pass":
        cut = next(b for b in actions if b.get("related") is a)
        return (f"{where}, {team}. {who}'s pass is cut out by {name(cut['player'])}.",
                f"{name(cut['player'])} cut out a {team} pass")
    if a["kind"] == "interception":
        return (f"{who} intercepts for {team}, {zone(*a['at'], a['side'])['words']}.",
                f"{who} won the ball back for {team}")
    if a["kind"] == "save":
        shooter = name(a["related"]["player"])
        return (f"Saved by {who}, who holds on.", f"{who} saved from {shooter}")
    if a["outcome"] == "goal":
        how = "heads it in" if a["body"] == "head" else "scores"
        goals = [b for b in actions if b["kind"] == "shot" and b["outcome"] == "goal" and b["f"] <= a["f"]]
        h = sum(1 for b in goals if b["side"] == "home")
        score = f"{team_word('home')} {h}, {team_word('away')} {len(goals) - h}"
        return (f"{where}, {team}. {who} {how}! Goal for {team}. {score}.", f"{who} scored for {team}")
    keeper = name(next(b for b in actions if b.get("related") is a)["player"])
    return (f"{where}, {team}. {who} shoots, saved by {keeper}.", f"{who} had a shot saved by {keeper}")


def priority(a) -> int:
    """0 routine, 1 notable, 2 big moment, 3 goal (higher = more important; catch-up uses >= 2)."""
    if a["kind"] == "shot":
        return 3 if a["outcome"] == "goal" else 2
    if a["kind"] == "save":
        return 2
    if a["kind"] == "interception" or a.get("sub") == "kick_off":
        return 1
    if a["kind"] == "pass" and a["end"] is not None:
        z = zone(*a["end"], a["side"])
        if z["in_box"] or (z["third"] == "attacking_third" and a["outcome"] == "successful"):
            return 1
    return 0


def build_signals(actions, ball):
    goals = [a for a in actions if a["kind"] == "shot" and a["outcome"] == "goal"]
    seconds = []
    for t in range(DURATION_S + 1):
        x, y, _, alive, side = ball[t * BALL_HZ]
        dng = {s: (r2(danger_of(x, y, s)) if alive and side == s else 0.0) for s in ("home", "away")}
        score = {s: sum(1 for g in goals if g["side"] == s and g["f_end"] <= t * BALL_HZ) for s in ("home", "away")}
        gd = score["home"] - score["away"]
        wp = win_prob(gd, t)
        ph, pa = P_BASE + P_DANGER * dng["home"] ** 2, P_BASE + P_DANGER * dng["away"] ** 2
        seconds.append(dict(t=t, score=score, poss=side if alive else None,
                            win_prob=dict(home=round(wp[0], 3), draw=round(wp[1], 3), away=round(wp[2], 3)),
                            suspense=round(suspense(gd, t, ph, pa), 4), danger=dng))
    # tension (file 39 tension_curve): suspense, plus a ramp over the 4 s before each shot weighted by xG only
    shots = [(a["f"] / BALL_HZ, a["f_end"] / BALL_HZ, a["side"], a["xg"], a["outcome"] == "goal")
             for a in actions if a["kind"] == "shot"]
    for row in seconds:
        t = row["t"]
        look = 0.0
        for ts, _, _, xg, _ in shots:
            w = min(1.0, xg / 0.3)
            if ts - 4.0 <= t < ts:
                look = max(look, w * (t - ts + 4.0) / 4.0)
            elif ts <= t < ts + 6.0:
                look = max(look, w * (1 - (t - ts) / 6.0))
        row["tension"] = r2(min(1.0, 0.65 * min(1.0, row["suspense"] / REF_SUSPENSE) + 0.35 * look))
    crowd = {end: crowd_states(seconds, shots, end) for end in ("H", "A")}
    for k, row in enumerate(seconds):
        row["crowd"] = {"H": crowd["H"][k], "A": crowd["A"][k]}
    per_second = [dict(t=r["t"], win_prob=r["win_prob"], suspense=r["suspense"], tension=r["tension"],
                       danger=r["danger"], crowd=r["crowd"], score=r["score"]) for r in seconds]
    one_shots = []
    for ts, tr, side, _, goal in shots:
        for end, me in (("H", "home"), ("A", "away")):
            one_shots.append(dict(t=round(tr, 2), end=end, kind=ONE_SHOT[("goal" if goal else "shot", side == me)]))
    events = {}
    for a in actions:
        spoken, spoken_past = spoken_lines(a, actions)
        events[a["id"]] = dict(t=round(a["f"] / BALL_HZ, 2), reveal_t=round(a["f_end"] / BALL_HZ, 2),
                               xg=a.get("xg"), priority=priority(a), zone=zone(*a["at"], a["side"]),
                               spoken=spoken, spoken_past=spoken_past)
    return dict(format="tely.signals", version=FORMAT_VERSION, match_id=MATCH_ID, hz=1,
                per_second=per_second, events=events, crowd_one_shots=one_shots)


# ---------------------------------------------------------------- 5. meta
def build_meta():
    teams = {}
    for side, t in TEAMS.items():
        teams[side] = dict(id=t["id"], name=t["name"], short_name=t["short_name"], formation=t["formation"],
                           attacks=t["attacks"], kit=t["kit"],
                           players=[dict(id=p[0], first_name=p[1], last_name=p[2], name=f"{p[1]} {p[2]}",
                                         jersey_number=p[3], position=p[4], is_starter=True)
                                    for p in PLAYERS[side]])
    return dict(
        format="tely.meta", version=FORMAT_VERSION, cdf_version=CDF_VERSION, synthetic=True,
        notice="Synthetic match. Fictional clubs and players. No real match data.",
        match=dict(id=MATCH_ID, competition="Berbata Synthetic League", season="2026-27",
                   kickoff_time=iso(0), venue=dict(id="syn_emberfield", name="Emberfield")),
        periods=[dict(period=PERIOD, start_time=iso(0), start_t=0.0, clock_start="00:00.00")],
        pitch=dict(length_m=2 * HALF_L, width_m=2 * HALF_W, origin="centre_spot",
                   x="metres along the touchline, -52.5..52.5; home attacks +x all match (CDF)",
                   y="metres across, -34..34, bottom to top: -34 is the near (main-stand) touchline"),
        teams=teams,
        judge_cut=dict(t_start=0.0, t_end=float(DURATION_S), seed=None, source="hand_written_sample"),
        rates=dict(ball_hz=BALL_HZ, player_hz=PLAYER_HZ, signals_hz=1),
        files=dict(events="events.jsonl", signals="signals.json", ticks="ticks.json.gz"),
    )


def build_ticks(ball, players):
    return dict(format="tely.ticks", version=FORMAT_VERSION, match_id=MATCH_ID, t0=0.0,
                duration_s=float(DURATION_S),
                ball=dict(hz=BALL_HZ, columns=["x", "y", "z", "alive", "poss"], rows=ball),
                players=dict(hz=PLAYER_HZ, ids=PLAYER_IDS, rows=players))


# ---------------------------------------------------------------- write
def _rows_json(obj: dict) -> str:
    """Readable but compact: one top-level key per line, and one list item / dict entry per line."""
    out = ["{"]
    items = list(obj.items())
    for k, (key, v) in enumerate(items):
        comma = "," if k < len(items) - 1 else ""
        if isinstance(v, list) and v and isinstance(v[0], dict):
            body = ",\n".join("    " + json.dumps(x, separators=(",", ":")) for x in v)
            out.append(f'  "{key}": [\n{body}\n  ]{comma}')
        elif isinstance(v, dict) and v and all(isinstance(x, dict) for x in v.values()) and key == "events":
            body = ",\n".join(f'    "{i}": ' + json.dumps(x, separators=(",", ":")) for i, x in v.items())
            out.append(f'  "{key}": {{\n{body}\n  }}{comma}')
        else:
            out.append(f'  "{key}": {json.dumps(v)}{comma}')
    out.append("}")
    return "\n".join(out) + "\n"


def build():
    actions, segs, anchors, goal_frame = build_script()
    ball = ball_track(segs, goal_frame)
    players = player_tracks(ball, anchors)
    events = cdf_lines(actions)
    signals = build_signals(actions, ball)
    return build_meta(), events, signals, build_ticks(ball, players)


def write(out_dir: Path) -> None:
    meta, events, signals, ticks = build()
    out_dir.mkdir(parents=True, exist_ok=True)
    # SEAM(B->A): meta.json -> A's commentator and relay read team names, kits, players (docs/match-format.md)
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8", newline="\n")
    # SEAM(B->A): events.jsonl -> A's planner reads CDF event lines (docs/match-format.md)
    (out_dir / "events.jsonl").write_text("".join(json.dumps(e, separators=(",", ":")) + "\n" for e in events),
                                          encoding="utf-8", newline="\n")
    # SEAM(B->A): signals.json -> A's templates read tension, xg, priority, zone, spoken (docs/match-format.md)
    (out_dir / "signals.json").write_text(_rows_json(signals), encoding="utf-8", newline="\n")
    # SEAM(B->A): ticks.json.gz -> A's commentary track pans the voice with ball x (docs/match-format.md)
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as gz:
        gz.write(json.dumps(ticks, separators=(",", ":")).encode("utf-8"))
    (out_dir / "ticks.json.gz").write_bytes(buf.getvalue())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "sample")
    write(ap.parse_args().out)
