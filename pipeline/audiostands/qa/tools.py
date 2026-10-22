"""The 8 Q&A tools (file 43 §3 schemas, ported from file 40's match_tools.py). OWNER: B (Nikolay).

Every tool takes the listener's playhead from the caller (A's relay injects it; the model never sets the clock) and
reads the match only through Bundle accessors that stop at the playhead (bundle.py). Each returns
{say, evidence_ids, as_of_clock, fragments} or {error, candidates}. `fragments` lists the FRAGMENTS ids that speak
`say` offline (None when the answer contains names or numbers no clip has, e.g. where_is).
"""
from __future__ import annotations

import difflib
import math
import re
from typing import Any

from .bundle import HALF_L, Bundle
from .fragments import STATIC, dist_frag, score_frag, zone_frag

THIRD_WORDS = {"defensive_third": "defensive third", "middle_third": "midfield", "attacking_third": "attacking third"}
SIDE_WORDS = {"near": "near side", "centre": "centre", "far": "far side"}


def _zone(b: Bundle, x: float, y: float, side: str) -> tuple[str, str]:
    """(third, side) from `side`'s point of view; same rule as interpret.zone (file 36)."""
    ax = x * b.attacks(side)
    third = "defensive_third" if ax < -17.5 else "middle_third" if ax < 17.5 else "attacking_third"
    s = "near" if y < -11.33 else "far" if y > 11.33 else "centre"
    return third, s


def _ok(b: Bundle, p: float, parts: list[tuple[str, str]] | None, say: str | None = None, evidence=(), **extra) -> dict:
    text = say if say is not None else " ".join(t for _, t in (parts or []))
    return {"say": text, "evidence_ids": list(evidence), "as_of_clock": b.clock_str(p),
            "fragments": [i for i, _ in parts] if parts is not None else None, **extra}


def _static(key: str) -> tuple[str, str]:
    return key, STATIC[key]


# ---------------------------------------------------------------- players
def find_player(b: Bundle, q: str) -> tuple[dict | None, dict | None]:
    """By shirt number ("9", "number 9", "Navy 9") or by name (fuzzy). Ambiguous -> {error, candidates}."""
    text = str(q).strip().lower()
    team = "home" if b.team_name("home").lower() in text else "away" if b.team_name("away").lower() in text else None
    pool = [p for p in b.players.values() if team is None or p["side"] == team]
    num = re.search(r"\b(\d{1,2})\b", text)
    if num:
        hits = [p for p in pool if p["jersey_number"] == int(num.group(1))]
    else:
        name = re.sub(r"\b(reds?|navy|number|no\.?)\b", " ", text).strip()
        keys: dict[str, list[dict]] = {}
        for p in pool:
            for k in (p["name"].lower(), p["last_name"].lower(), p["first_name"].lower()):
                keys.setdefault(k, []).append(p)
        close = difflib.get_close_matches(name, list(keys), n=3, cutoff=0.6)
        hits = list({p["id"]: p for k in close for p in keys[k]}.values())
        if close and close[0] in (name,) and len(keys[close[0]]) == 1:
            hits = keys[close[0]]
    if len(hits) != 1:
        cands = [f"{p['name']} ({b.team_name(p['side'])} #{p['jersey_number']})" for p in (hits or pool)[:4]]
        return None, {"error": "ambiguous_or_unknown_player", "candidates": cands}
    return hits[0], None


def _player_xy(b: Bundle, pid: str, p: float) -> tuple[float, float, list[list[float]]]:
    ids, rows = b.player_rows(p)
    j = ids.index(pid)
    last = rows[-1]
    return last[2 * j], last[2 * j + 1], [[r[2 * j], r[2 * j + 1]] for r in rows]


# ---------------------------------------------------------------- the 8 tools
def get_score_and_clock(b: Bundle, p: float) -> dict:
    sc = b.score(p)
    minute = int(math.floor(b.clock_s(b.clamp(p)) / 60))
    goals = [e["id"] for e in b.known(p) if e["type"] == "shot" and e["outcome_type"] == "successful"]
    return _ok(b, p, [score_frag(b.team_name("home"), b.team_name("away"), minute, sc["home"], sc["away"])],
               evidence=goals)


def get_ball_position(b: Bundle, p: float) -> dict:
    ball = b.ball(p)
    known = b.known(p)
    ev = [known[-1]["id"]] if known else []
    if not ball["alive"] or not ball["poss"]:
        return _ok(b, p, [_static("ball_out")], evidence=ev, x=ball["x"], y=ball["y"])
    side = ball["poss"]
    third, s = _zone(b, ball["x"], ball["y"], side)
    key = "H" if side == "home" else "A"
    goal_x = HALF_L * b.attacks(side)
    d = math.hypot(goal_x - ball["x"], ball["y"])
    return _ok(b, p, [zone_frag(b.team_name(side), key, third, s), dist_frag(d)], evidence=ev, x=ball["x"], y=ball["y"])


def where_is(b: Bundle, p: float, player: str) -> dict:
    pl, err = find_player(b, player)
    if err:
        return err
    x, y, _ = _player_xy(b, pl["id"], p)
    ball = b.ball(p)
    third, s = _zone(b, x, y, pl["side"])
    d = round(math.hypot(x - ball["x"], y - ball["y"]))
    say = f"{pl['name']} of {b.team_name(pl['side'])} is in the {THIRD_WORDS[third]}, {SIDE_WORDS[s]}, {d} metres from the ball."
    return _ok(b, p, None, say=say, evidence=[f"track:{pl['id']}@{b.clock_str(p)}"])


def get_player_stats(b: Bundle, p: float, player: str, metrics: list[str] | None = None) -> dict:
    pl, err = find_player(b, player)
    if err:
        return err
    _, _, path = _player_xy(b, pl["id"], p)
    hz = b.ticks["players"]["hz"]
    steps = [math.hypot(q[0] - a[0], q[1] - a[1]) for a, q in zip(path, path[1:])]
    known = [e for e in b.known(p) if e.get("player_id") == pl["id"]]
    passes = [e for e in known if e["type"] == "pass"]
    shots = [e for e in known if e["type"] == "shot"]
    mins = max(1, round((b.clamp(p) - b.t0) / 60))
    m = {"distance_km": round(sum(steps) / 1000, 2),
         "top_speed_kmh": round(max(steps, default=0.0) * hz * 3.6, 1),
         "passes": f"{sum(1 for e in passes if e['is_successful'])} of {len(passes)}",
         "shots": len(shots)}
    m = {k: v for k, v in m.items() if not metrics or k in metrics}
    shots_n = len(shots)
    said = {"distance_km": f"ran {round(sum(steps))} metres",
            "top_speed_kmh": f"top speed {round(max(steps, default=0.0) * hz * 3.6, 1)} kilometres an hour",
            "passes": f"completed {sum(1 for e in passes if e['is_successful'])} of {len(passes)} passes",
            "shots": f"{shots_n} shot" + ("" if shots_n == 1 else "s")}
    when = "In the last minute" if mins == 1 else f"In the last {mins} minutes"
    say = f"{when}, {pl['name']} " + ", ".join(said[k] for k in m) + "."
    return _ok(b, p, None, say=say, evidence=[e["id"] for e in passes + shots], metrics=m)


def get_last_events(b: Bundle, p: float, n: int = 3) -> dict:
    ev = [e for e in b.known(p) if b.sig(e["id"])["priority"] >= 1][-max(1, min(int(n), 5)):][::-1]
    if not ev:
        return _ok(b, p, [_static("nothing_yet")])
    parts: list[tuple[str, str]] = []
    for i, e in enumerate(ev):
        if i:
            parts.append(_static("then"))
        parts.append((f"ev_{e['id']}", b.sig(e["id"])["spoken"]))
    return _ok(b, p, parts, evidence=[e["id"] for e in ev])


def explain_moment(b: Bundle, p: float, moment_id: str) -> dict:
    known = {e["id"]: e for e in b.known(p)}
    e = known.get(moment_id)
    if e is None:                       # unknown, or not yet revealed at this playhead: never confirm it exists
        recent = [x["id"] for x in list(known.values()) if b.sig(x["id"])["priority"] >= 1][-3:][::-1]
        return {"error": "unknown_moment", "candidates": recent, "hint": "call get_last_events first"}
    s = b.sig(e["id"])
    extra = ""
    if e["type"] == "shot" and s["xg"] is not None:
        if e["outcome_type"] == "successful":
            sc = b.score(s["reveal_t"])
            extra = f" That made it {b.team_name('home')} {sc['home']}, {b.team_name('away')} {sc['away']}."
        else:
            size = "big" if s["xg"] >= 0.3 else "good" if s["xg"] >= 0.1 else "half"
            extra = f" A {size} chance: about {round(s['xg'] * 100)} in 100 shots like that go in."
    elif e.get("outcome_type") == "yellow_card":
        extra = " A booking, so that player has to be careful now."
    elif e["type"] in ("defending", "goalkeeping"):
        extra = f" It happened in the {s['zone']['words']}."
    return _ok(b, p, None, say=s["spoken"] + extra, evidence=[e["id"]])


def _missed(b: Bundle, since: float, until: float) -> list[dict]:
    """Big moments (priority >= 2) that started after `since` and were revealed by `until`; top 2, in time order."""
    m = [e for e in b.events if since < b.sig(e["id"])["t"] <= until and b.sig(e["id"])["reveal_t"] <= until
         and b.sig(e["id"])["priority"] >= 2]
    top: list[dict] = []
    for e in sorted(m, key=lambda e: (-b.sig(e["id"])["priority"], b.sig(e["id"])["t"])):
        if e["type"] == "goalkeeping" and any(t["id"] in (e.get("related_event_ids") or ()) for t in top):
            continue                    # a shot and its save are one moment: say it once
        top.append(e)
        if len(top) == 2:
            break
    return sorted(top, key=lambda e: b.sig(e["id"])["t"])


def _missed_parts(b: Bundle, lead: str, events: list[dict]) -> list[tuple[str, str]]:
    parts = [_static(lead)]
    for i, e in enumerate(events):
        if i:
            parts.append(_static("and"))
        parts.append((f"past_{e['id']}", b.sig(e["id"])["spoken_past"]))
    return parts


def what_did_i_miss(b: Bundle, p: float, since: str) -> dict:
    s = b.parse_clock(since)
    if s is None:
        return {"error": "bad_time", "candidates": [b.clock_str(max(b.t0, p - 60))], "hint": "use mm:ss match time"}
    ev = _missed(b, s, b.clamp(p))
    if not ev:
        return _ok(b, p, [_static("nothing_missed")])
    parts = _missed_parts(b, "while_away", ev)
    return _ok(b, p, parts, say=" ".join(t for _, t in parts) + ".", evidence=[e["id"] for e in ev])


def set_preferences(b: Bundle, p: float, **prefs: Any) -> dict:
    allowed = {"verbosity": {"describer", "radio", "calm"}, "haptics": {"off", "events", "full"}}
    clean: dict[str, Any] = {}
    for k, v in prefs.items():
        if k in allowed and v in allowed[k]:
            clean[k] = v
        elif k == "crowd_mix" and isinstance(v, (int, float)):
            clean[k] = min(1.0, max(0.0, float(v)))
    # SEAM(B->A): the relay publishes `prefs` to the listener's page; nothing here touches the match.
    return _ok(b, p, [_static("done")], prefs=clean)


TOOLS = {f.__name__: f for f in (get_score_and_clock, get_ball_position, where_is, get_player_stats, get_last_events,
                                 explain_moment, what_did_i_miss, set_preferences)}


def call(name: str, args: dict[str, Any], playhead_s: float, bundle: Bundle) -> dict[str, Any]:
    fn = TOOLS.get(name)
    if fn is None:
        return {"error": "unknown_tool", "candidates": sorted(TOOLS)}
    p = bundle.clamp(playhead_s)
    clean = {k: v for k, v in (args or {}).items() if k not in ("playhead_s", "session_id")}   # never trust a clock
    try:
        return fn(bundle, p, **clean)
    except TypeError as e:
        return {"error": "bad_arguments", "candidates": [], "hint": str(e)}
