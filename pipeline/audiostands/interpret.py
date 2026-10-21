"""Interpret: the per-second and per-event signals in signals.json (contracts/README.md). OWNER: B (Nikolay).

Per second: win probability (file 23 live Poisson), suspense (file 39), tension 0-1 (file 39 tension_curve,
look-ahead weighted by xG only) and danger per team (Berbata definition, below). The crowd is in crowd.py.
Per event: t, reveal_t, xg, priority, zone (file 36 ball-first words), spoken, spoken_past.

    python -m audiostands.interpret --calibrate      # recompute REF_SUSPENSE (p99 over seeds 1-20)
"""
from __future__ import annotations

import argparse
import math

from .generator import DIR, FPS, HALF_L, PERIODS, TEAMS

LAM = {"home": 1.5, "away": 1.2}   # pre-match expected goals (file 23 worked example uses 1.5 v 1.1; ours, home edge)
K_PRIOR = 90.0                     # file 23: prior worth k minutes of play (k = 90 in its worked outputs)
MATCH_MIN = 95.0                   # file 23: expected end incl. added time (M = 95)
P_BASE, P_DANGER = 0.0003, 0.04    # P(goal in the next second) = P_BASE + P_DANGER * danger^2 (ours)
REF_SUSPENSE = 0.1158             # p99 of per-second suspense over seeds 1-20 (python -m audiostands.interpret --calibrate)
W_LOOK, LEAD_S, TAIL_S = 0.35, 4.0, 6.0   # file 39 tension_curve


# ---------------------------------------------------------------- shared helpers
def zone(x: float, y: float, side: str) -> dict:
    """Ball-first zone words (file 36): third from the acting team's view, side absolute (near = y < 0)."""
    ax = x * DIR[side]
    third = "defensive_third" if ax < -17.5 else "middle_third" if ax < 17.5 else "attacking_third"
    s = "near" if y < -11.33 else "far" if y > 11.33 else "centre"
    words = {"defensive_third": "defensive third", "middle_third": "midfield", "attacking_third": "attacking third"}
    words = words[third] + ", " + {"near": "near side", "far": "far side", "centre": "centre"}[s]
    return dict(third=third, side=s, in_box=ax > HALF_L - 16.5 and abs(y) < 20.16, words=words)


def danger_of(x: float, y: float, side: str) -> float:
    """Berbata definition (v0): how close the team with the ball is to scoring, 0..1:
    (1 - distance to the goal it attacks / 40 m) ^ 1.5, and 0 beyond 40 m."""
    return max(0.0, 1 - math.hypot(HALF_L * DIR[side] - x, y) / 40.0) ** 1.5


def _pois(k: int, mu: float) -> float:
    return math.exp(-mu) * mu ** k / math.factorial(k)


def win_prob(gd: int, minute: float, r_h: float, r_a: float) -> list:
    """File 23 Poisson grid over the goals still to come -> [home, draw, away]."""
    left = max(MATCH_MIN - minute, 0.0)
    mh, ma = r_h * left, r_a * left
    ph, pa = [_pois(k, mh) for k in range(11)], [_pois(k, ma) for k in range(11)]
    out = [0.0, 0.0, 0.0]
    for x in range(11):
        for y in range(11):
            d = gd + x - y
            out[0 if d > 0 else 1 if d == 0 else 2] += ph[x] * pa[y]
    s = out[0] + out[1] + out[2]
    return [v / s for v in out]


def live_rates(minute: float, xg_h: float, xg_a: float):
    """File 23 Gamma-Poisson shrinkage: the pre-match rate counts as K_PRIOR minutes of play (goals/min)."""
    return ((LAM["home"] / 90 * K_PRIOR + xg_h) / (K_PRIOR + minute),
            (LAM["away"] / 90 * K_PRIOR + xg_a) / (K_PRIOR + minute))


def suspense(gd, minute, r_h, r_a, ph, pa) -> float:
    """File 39 (Ely et al.): spread of the win-probability outcomes one second from now."""
    mu, bh, ba = win_prob(gd, minute, r_h, r_a), win_prob(gd + 1, minute, r_h, r_a), win_prob(gd - 1, minute, r_h, r_a)
    p0 = 1 - ph - pa
    b0 = [(mu[i] - ph * bh[i] - pa * ba[i]) / p0 for i in range(3)]
    sq = lambda b: sum((b[i] - mu[i]) ** 2 for i in range(3))
    return math.sqrt(ph * sq(bh) + pa * sq(ba) + p0 * sq(b0))


def r2(v):
    return round(v + 0.0, 2)


# ---------------------------------------------------------------- match state over time
class State:
    """Score, xG so far and minute at a (period, t) moment, counting only what is known by then."""

    def __init__(self, match: dict):
        self.events = match["events"]
        self.goals = [(PERIODS.index(e["period"]), e["reveal_f"], e["team"]) for e in self.events
                      if e["type"] == "shot" and e["outcome_type"] == "successful"]
        self.shots = [(PERIODS.index(e["period"]), e["f"], e["team"], e["xg"]) for e in self.events
                      if e["type"] == "shot"]

    def score(self, k: int, f: int) -> dict:
        s = {"home": 0, "away": 0}
        for pk, rf, side in self.goals:
            if (pk, rf) <= (k, f):
                s[side] += 1
        return s

    def xg_so_far(self, k: int, f: int) -> dict:
        s = {"home": 0.0, "away": 0.0}
        for pk, sf, side, x in self.shots:
            if (pk, sf) <= (k, f):
                s[side] += x
        return s


def per_second(match: dict, k: int, t0: int, t1: int, ball: list) -> list:
    """Rows for whole seconds t0..t1 (period-relative). ball = 25 Hz rows starting at t0."""
    st = State(match)
    rows = []
    for t in range(t0, t1 + 1):
        x, y, _, alive, side = ball[(t - t0) * FPS]
        dng = {s: (r2(danger_of(x, y, s)) if alive and side == s else 0.0) for s in ("home", "away")}
        f = t * FPS
        score, xgs = st.score(k, f), st.xg_so_far(k, f)
        minute = 45 * k + t / 60
        r_h, r_a = live_rates(minute, xgs["home"], xgs["away"])
        gd = score["home"] - score["away"]
        wp = win_prob(gd, minute, r_h, r_a)
        ph, pa = P_BASE + P_DANGER * dng["home"] ** 2, P_BASE + P_DANGER * dng["away"] ** 2
        bh, ba = win_prob(gd + 1, minute, r_h, r_a), win_prob(gd - 1, minute, r_h, r_a)
        rows.append(dict(t=t, win_prob=dict(home=round(wp[0], 3), draw=round(wp[1], 3), away=round(wp[2], 3)),
                         suspense=round(suspense(gd, minute, r_h, r_a, ph, pa), 4), danger=dng, score=score,
                         poss=side if alive else None,
                         leverage=round(min(1.0, abs(bh[0] - ba[0]) / 2), 3)))
    shots = [(e["f"] / FPS, e["xg"]) for e in match["events"] if e["type"] == "shot" and e["period"] == PERIODS[k]]
    for row in rows:
        t, look = row["t"], 0.0
        for ts, xg in shots:                       # look-ahead ramp from pre-shot xG only (never the outcome)
            w = min(1.0, xg / 0.3)
            if ts - LEAD_S <= t < ts:
                look = max(look, w * (t - ts + LEAD_S) / LEAD_S)
            elif ts <= t < ts + TAIL_S:
                look = max(look, w * (1 - (t - ts) / TAIL_S))
        row["tension"] = r2(min(1.0, (1 - W_LOOK) * min(1.0, row["suspense"] / REF_SUSPENSE) + W_LOOK * look))
    return rows


# ---------------------------------------------------------------- per event
def priority(e: dict) -> int:
    """0 routine, 1 notable, 2 big moment, 3 goal (higher = more important; catch-up uses >= 2, file 40)."""
    if e["type"] == "shot":
        return 3 if e["outcome_type"] == "successful" else 2
    if e["type"] in ("goalkeeping", "referee") or e.get("outcome_type") in ("yellow_card", "red_card"):
        return 2
    if e["type"] in ("defending", "misc") or e.get("sub_type") == "kick_off":
        return 1
    if e["type"] == "pass" and e["x_end"] is not None:
        z = zone(e["x_end"], e["y_end"], e["team"])
        if z["in_box"] or (z["third"] == "attacking_third" and e["is_successful"]):
            return 1
    return 0


def spoken_lines(e: dict, match: dict, by_id: dict) -> tuple[str, str]:
    """(spoken, spoken_past). Ball first (file 36): where, which team, then who. Contains the outcome, so it is
    only safe after reveal_t. spoken_past is a fragment for "While we talked, A and B." (file 40)."""
    P = match["players"]
    name = lambda pid: P[pid]["last"]
    if e["type"] == "referee":
        shot = by_id[e["related_event_ids"][0]]
        team = TEAMS[shot["team"]]["short_name"]
        if e["outcome_type"] == "goal_stands":
            return (f"VAR checks the {team} goal... and it stands.", f"VAR let the {team} goal stand")
        return (f"VAR checks the {team} goal... and rules it out.", f"VAR ruled out a {team} goal")
    side = e["team"]
    team, who = TEAMS[side]["short_name"], name(e["player_id"])
    where = zone(e["x"], e["y"], side)["words"]
    Where = where[0].upper() + where[1:]
    rel = [by_id[i] for i in e["related_event_ids"] or () if i in by_id]
    if e["type"] == "pass":
        lead = {"kick_off": "Kick-off", "free_kick": "Free kick", "goal_kick": "Goal kick"}.get(e["sub_type"])
        head = f"{lead}, {team}." if lead else f"{Where}, {team}."
        if e["is_successful"]:
            rec = name(e["receiver_id"])
            z_end = zone(e["x_end"], e["y_end"], side)
            if z_end["in_box"] and zone(e["x"], e["y"], side)["side"] != "centre":
                return (f"{head} {who} crosses for {rec}.", f"{who} crossed for {rec}")
            return (f"{head} {who} to {rec}.", f"{who} found {rec}")
        cut = name(rel[0]["player_id"]) if rel else "a defender"
        return (f"{head} {who}'s pass is cut out by {cut}.", f"{cut} cut out a {team} pass")
    if e["type"] == "defending":
        verb = {"interception": "intercepts", "block": "blocks it"}.get(e["sub_type"], "clears")
        past = {"interception": f"{who} won the ball back for {team}", "block": f"{who} blocked a shot"}
        return (f"{who} {verb} for {team}, {where}.", past.get(e["sub_type"], f"{who} cleared for {team}"))
    if e["type"] == "goalkeeping":
        shooter = name(rel[0]["player_id"]) if rel else "the shot"
        return (f"Saved by {who}, who holds on.", f"{who} saved from {shooter}")
    if e["type"] == "misc":
        if e["outcome_type"] == "yellow_card":
            return (f"Foul by {who} of {team}, {where}. Yellow card.", f"{who} was booked")
        return (f"Foul by {who} of {team}, {where}.", f"{who} gave away a free kick")
    out = e["outcome_type"]                                   # shot
    if out == "successful":
        how = "heads it in" if e["body_part"] == "head" else "scores"
        return (f"{Where}, {team}. {who} {how}! Goal for {team}.", f"{who} scored for {team}")
    if out == "offside":
        return (f"{Where}, {team}. {who} puts it in, but VAR rules it out.", f"{who} had a goal ruled out")
    if out == "saved":
        keeper = name(rel[0]["player_id"]) if rel else "the keeper"
        return (f"{Where}, {team}. {who} shoots, saved by {keeper}.", f"{who} had a shot saved by {keeper}")
    tail = {"wide": "wide", "woodwork": "off the post", "blocked": "blocked"}[out]
    past = {"wide": f"{who} shot wide", "woodwork": f"{who} hit the post", "blocked": f"{who} had a shot blocked"}[out]
    return (f"{Where}, {team}. {who} shoots, {tail}.", past)


def event_signals(events: list, match: dict) -> dict:
    by_id = {e["id"]: e for e in match["events"]}
    out = {}
    for e in events:
        side = e["team"] or e.get("var_team")
        spoken, spoken_past = spoken_lines(e, match, by_id)
        out[e["id"]] = dict(t=round(e["f"] / FPS, 2), reveal_t=round(e["reveal_f"] / FPS, 2), xg=e["xg"],
                            priority=priority(e), zone=zone(e["x"], e["y"], side), spoken=spoken,
                            spoken_past=spoken_past)
    return out


# ---------------------------------------------------------------- calibration
def calibrate(seeds=range(1, 21)) -> float:
    """p99 of per-second suspense over whole matches (file 39: normalise globally, not per window)."""
    from .generator import generate
    from .movement import ball_rows
    vals = []
    for s in seeds:
        m = generate(s)
        for k, per in enumerate(m["periods"]):
            n = per["end_f"] // FPS
            ball = ball_rows(per["keys"], 0, n * FPS)
            vals += [r["suspense"] for r in per_second(m, k, 0, n, ball)]
    vals.sort()
    return vals[int(0.99 * (len(vals) - 1))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    if ap.parse_args().calibrate:
        print(f"REF_SUSPENSE = {calibrate():.4f}")
