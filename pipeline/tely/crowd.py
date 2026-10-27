"""Crowd state per end, once a second, plus one-shot reactions (file 38 crowd_states).

Spoiler rule: the look-ahead (an anticipation swell before a shot) uses the shot's time and xG only, so a goal and
a miss build the same swell. Reactions start at the moment the outcome is revealed (reveal_t), never before.
"""
from __future__ import annotations

import math

from .generator import FPS, PERIODS

REACT = {  # file 38: (d_excitement, d_valence, tau_s) from the listening end's view, after the event
    ("goal", True): (1.00, 1.00, 25), ("goal", False): (0.30, -0.90, 30),
    ("shot", True): (0.55, -0.35, 5), ("shot", False): (0.25, 0.35, 4),     # our miss = groan, theirs = relief
    ("foul", True): (0.15, 0.10, 3), ("foul", False): (0.30, -0.30, 4),
    ("card", True): (0.20, -0.30, 5), ("card", False): (0.25, 0.25, 5)}
VAR_HOLD_S = 20.0           # file 38: VAR-like pause = hushed hold for about 20 s
# Look-ahead strength. File 38 used min(1, 2 * xg) and 0.5; ours are stronger so that every xG >= 0.1 chance
# swells the home end by >= 0.2 over 8 s (test; "tune the crowd weights, not the test").
ANTIC_XG, W_ANTIC = 4.0, 0.9
# One-shot clip names B's CrowdEngine plays (docs/match-format.md lists them).
ONE_SHOT = {("goal", True): "roar", ("goal", False): "stunned_hush", ("shot", True): "ooh_groan",
            ("shot", False): "relief_applause", ("foul", False): "whistles_jeer", ("card", False): "cheer"}


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def moments(events: list, k: int) -> dict:
    """What the crowd can know, from one period's events: shots (look-ahead by xG), reactions, VAR holds."""
    per = PERIODS[k]
    shots, reacts, holds = [], [], []
    for e in events:
        if e["period"] != per:
            continue
        t, tr = e["f"] / FPS, e["reveal_f"] / FPS
        if e["type"] == "shot":
            shots.append((t, e["team"], e["xg"]))
            kind = "goal" if e["outcome_type"] == "successful" else "shot"
            reacts.append((tr, kind, e["team"], e["id"]))
        elif e["type"] == "misc":
            reacts.append((t, "foul", e["team"], e["id"]))
            if e["outcome_type"] == "yellow_card":
                reacts.append((t, "card", e["team"], e["id"]))
        elif e["type"] == "referee" and e["sub_type"] == "var_check":
            holds.append((t, tr))
    return dict(shots=shots, reacts=reacts, holds=holds)


def crowd_states(rows: list, mo: dict, end: str, lookahead_s: float = 8.0, lead_s: float = 5.0,
                 warm: list | None = None) -> list:
    """File 38 crowd_states for one end ("H" home end, "A" away end). rows: per-second signal rows (t, poss,
    danger, score, leverage). warm: earlier rows used only to settle the smoothing before the window."""
    me = "home" if end == "H" else "away"
    out, exc_s, val_s, dang_s = [], 0.15, 0.0, 0.0
    up, dn = 1 - math.exp(-1 / 0.8), 1 - math.exp(-1 / 4.0)
    for row in (warm or []) + rows:
        t = row["t"]
        poss = row["poss"]
        mine = 0.0 if poss is None else (1.0 if poss == me else -1.0)
        danger = mine * (row["danger"][poss] if poss else 0.0)
        antic = sum((1 if side == me else -1) * min(1.0, ANTIC_XG * xg) * smoothstep(1 - (ts - t) / lead_s)
                    for ts, side, xg in mo["shots"] if t < ts <= t + lookahead_s)
        de = dv = 0.0
        for tr, kind, side, _ in mo["reacts"]:
            if tr <= t:
                d_e, d_v, tau = REACT[(kind, side == me)]
                w = math.exp(-(t - tr) / tau)
                de, dv = de + d_e * w, dv + d_v * w
        diff = (row["score"]["home"] - row["score"]["away"]) * (1 if end == "H" else -1)
        lev = row["leverage"]
        exc = 0.15 + 0.25 * lev + 0.35 * abs(danger) + W_ANTIC * abs(antic) + de
        val = 0.5 * math.tanh(0.5 * diff) + 0.4 * danger + 0.3 * antic + dv
        if any(a <= t < min(b, a + VAR_HOLD_S) for a, b in mo["holds"]):     # VAR-like hush
            exc, val = 0.35 + 0.3 * lev, 0.0
        exc, val = max(0.0, min(1.0, exc)), max(-1.0, min(1.0, val))
        exc_s += (up if exc > exc_s else dn) * (exc - exc_s)
        val_s += (1 - math.exp(-1 / 2.0)) * (val - val_s)
        dang_s += (1 - math.exp(-1 / 1.5)) * (danger + 0.5 * antic - dang_s)
        out.append(dict(excitement=round(exc_s + 0.0, 2), valence=round(val_s + 0.0, 2),
                        danger=round(max(-1.0, min(1.0, dang_s)) + 0.0, 2)))
    return out[len(warm or []):]


def one_shots(mo: dict, t0: float, t1: float) -> list:
    """Clips to fire once at the reveal moment, per end. A VAR check starts with a "hush" at both ends."""
    out = []
    for tr, kind, side, eid in mo["reacts"]:
        if not t0 <= tr <= t1:
            continue
        for end, me in (("H", "home"), ("A", "away")):
            clip = ONE_SHOT.get((kind, side == me))
            if clip:
                out.append(dict(t=round(tr, 2), end=end, kind=clip))
    for a, _ in mo["holds"]:
        if t0 <= a <= t1:
            out += [dict(t=round(a, 2), end="H", kind="hush"), dict(t=round(a, 2), end="A", kind="hush")]
    out.sort(key=lambda o: (o["t"], o["end"]))
    return out
