"""The 8 Q&A tools (file 43 §3 schemas, ported from file 40's match_tools.py).

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
_NOT_NAMES = {"where", "is", "the", "how", "far", "has", "have", "run", "ran", "made", "many", "passes", "pass", "stats",
              "stat", "for", "of", "did", "does", "what", "about", "player", "fast", "shots", "shot", "got", "scored",
              "played", "doing", "now", "right", "and", "his", "her", "their", "reds", "red", "navy", "number", "keeper"}
SURNAME_MIN, FIRST_MIN, CLEAR_MARGIN = 0.75, 0.85, 0.1   # ours: tuned on eval/qa_cases.jsonl (typos, shared first names)
NEAR_MIN = 0.65  # ours: nothing matched -> offer names this close (speech-to-text "Tio" for Teo, A7 golden turns)


def _match_names(pool: list[dict], text: str) -> list[dict]:
    """Players the words in `text` point to. A close surname scores its similarity (typos are fine); an exact first
    name adds 0.5. One clear winner (>= CLEAR_MARGIN ahead of the next) is returned alone; a tie returns all tied
    (e.g. "Gus" when two players are called Gus), so the caller asks "Which player?"."""
    words = [w for w in re.findall(r"[a-z][a-z'-]+", text) if w not in _NOT_NAMES and len(w) >= 3]
    ratio = lambda a, c: difflib.SequenceMatcher(None, a, c).ratio()
    scored = []
    for p in pool:
        last = max((ratio(w, p["last_name"].lower()) for w in words), default=0.0)
        first = max((ratio(w, p["first_name"].lower()) for w in words), default=0.0)
        s = (last if last >= SURNAME_MIN else 0.0) + (0.5 if first >= FIRST_MIN else 0.0)
        if s > 0:
            scored.append((s, p))
    if not scored:
        return []
    scored.sort(key=lambda x: -x[0])
    top = scored[0][0]
    return [p for s, p in scored if s > top - CLEAR_MARGIN]


def _near_names(pool: list[dict], text: str) -> list[dict]:
    """Nothing matched: the players whose first or last name is closest (>= NEAR_MIN) to a word, as "did you mean"
    candidates. Never a random list: the model would read it out as if it were a real choice."""
    words = [w for w in re.findall(r"[a-z][a-z'-]+", text) if w not in _NOT_NAMES and len(w) >= 3]
    ratio = lambda a, c: difflib.SequenceMatcher(None, a, c).ratio()
    scored = [(max((ratio(w, n.lower()) for w in words for n in (p["first_name"], p["last_name"])), default=0.0), p)
              for p in pool]
    top = max((s for s, _ in scored), default=0.0)
    return [p for s, p in scored if s >= NEAR_MIN and s > top - CLEAR_MARGIN]


def find_player(b: Bundle, q: str) -> tuple[dict | None, dict | None]:
    """By shirt number ("9", "number 9", "Navy 9") or by name (fuzzy). Ambiguous -> {error, candidates}."""
    text = str(q).strip().lower()
    # "Reds", "Red", "Red's": the live model rewrites what the fan said ("Red keeper", A7 golden turns).
    said = lambda side: re.search(rf"\b{re.escape(b.team_name(side).lower().rstrip('s'))}s?\b", text)
    team = "home" if said("home") else "away" if said("away") else None
    pool = [p for p in b.players.values() if team is None or p["side"] == team]
    num = re.search(r"\b(\d{1,2})\b", text)
    names = _match_names(pool, text)
    near = False
    if num:
        nums = [p for p in pool if p["jersey_number"] == int(num.group(1))]
        both = [p for p in nums if p in names]
        # "Gus Fenford #9": the name picks one of the two number 9s. A name and a number that disagree -> ask.
        hits = both or (nums + [p for p in names if p not in nums] if names else nums)
    elif re.search(r"\b(goal)?keeper\b|\bgoalie\b", text):
        hits = [p for p in pool if p["position"] == "GK"]       # "the keeper" -> both, "Reds keeper" -> one
    else:
        hits = names or _near_names(pool, text)
        near = not names
    if len(hits) != 1 or near:                                  # a near miss ("Tio") is a question, never an answer
        cands = [f"{p['name']} ({b.team_name(p['side'])} #{p['jersey_number']})" for p in hits[:4]]
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
    # Same second as the score row: a goal revealed at 703.76 counts from 704, so the evidence never contradicts "nil".
    goals = [e["id"] for e in b.known(math.floor(p)) if e["type"] == "shot" and e["outcome_type"] == "successful"]
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
    """Big moments (priority >= 2) whose outcome was revealed in (since, until]; top 2, in time order.
    Filter on reveal_t, not the start: a goal struck before the Ask but confirmed by VAR during it is news."""
    m = [e for e in b.events if since < b.sig(e["id"])["reveal_t"] <= until and b.sig(e["id"])["priority"] >= 2]
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


def catch_up_answer(b: Bundle, since_s: float, until_s: float) -> dict:
    """"Back to the action", plus the big moments revealed while the fan was asking (file 40 catch_up_line)."""
    until = b.clamp(until_s)
    ev = _missed(b, since_s, until)
    if not ev:
        return _ok(b, until, [_static("back")])
    parts = [_static("back")] + _missed_parts(b, "while_we_talked", ev)
    return _ok(b, until, parts, say=" ".join(t for _, t in parts) + ".", evidence=[e["id"] for e in ev])


def what_did_i_miss(b: Bundle, p: float, since: str) -> dict:
    s = b.parse_clock(since)
    if s is None:
        return {"error": "bad_time", "candidates": [b.clock_str(max(b.t0, p - 60))], "hint": "use mm:ss match time"}
    ev = _missed(b, s, b.clamp(p))
    if not ev:
        return _ok(b, p, [_static("nothing_missed")])
    parts = _missed_parts(b, "while_away", ev)
    return _ok(b, p, parts, say=" ".join(t for _, t in parts) + ".", evidence=[e["id"] for e in ev])


RECAP_LEAD = {"so_far": "recap", "half_time": "recap_ht", "end": "recap_end"}
RECAP_MAX = 6   # big moments in one recap: the latest six, so it stays under about 20 s


def get_recap(b: Bundle, p: float, moment: Any = "so_far") -> dict:
    """Half-time, the end, or "so far" (Tier 1 item 7): the score, then each big moment revealed by p, in time
    order. Only verified fragments (the score line and the events' spoken_past), clamped to the playhead like every
    tool, so a recap can never say what hasn't happened yet. No LLM."""
    p = b.clamp(p)
    lead = RECAP_LEAD.get(moment, "recap")
    big = sorted((e for e in b.events if b.sig(e["id"])["reveal_t"] <= p and b.sig(e["id"])["priority"] >= 2),
                 key=lambda e: b.sig(e["id"])["t"])
    keep: list[dict] = []
    for e in big:
        if e["type"] == "goalkeeping" and any(k["id"] in (e.get("related_event_ids") or ()) for k in keep):
            continue                    # a shot and its save are one moment: say it once (as _missed does)
        keep.append(e)
    keep = keep[-RECAP_MAX:]
    sc = b.score(p)
    minute = int(math.floor(b.clock_s(p) / 60))
    parts = [_static(lead), score_frag(b.team_name("home"), b.team_name("away"), minute, sc["home"], sc["away"])]
    parts += [(f"past_{e['id']}", b.sig(e["id"])["spoken_past"]) for e in keep] or [_static("nothing_yet")]
    say = " ".join(t for _, t in parts[:2]) + " " + ". ".join(t.rstrip(".") for _, t in parts[2:]) + "."
    return _ok(b, p, parts, say=say, evidence=[e["id"] for e in keep], moment=lead)


NO_DETAIL_LEVEL = ("I can do key moments only, or the full radio commentary. Say which you'd like.")
DETAIL_SAID = {"key": "Key moments only from now on: chances, goals and cards.",
               "full": "The full radio commentary from now on."}


def set_preferences(b: Bundle, p: float, **prefs: Any) -> dict:
    allowed = {"haptics": {"off", "events", "full"}, "detail": {"key", "full"}}
    clean: dict[str, Any] = {}
    for k, v in prefs.items():
        if k in allowed and v in allowed[k]:
            clean[k] = v
        elif k == "crowd_mix" and isinstance(v, (int, float)):
            clean[k] = min(1.0, max(0.0, float(v)))
    # A follow or detail request carries no vibration or crowd change: the live model was seen filling those in
    # (27 Oct: "follow Olvholm" arrived with haptics="events", detail="full"), and a fan's settings must never move
    # unasked. "Turn the crowd down and the vibration off" still works: neither is follow nor detail.
    if "follow" in prefs or "detail" in clean:
        clean = {k: v for k, v in clean.items() if k == "detail" and "follow" not in prefs}
    if "follow" in prefs:      # D34: follow one player all match ("follow Olvholm", "stop following")
        q = str(prefs["follow"] or "").strip()
        if q.lower() in ("", "none", "nobody", "no one", "stop", "off"):
            return _ok(b, p, None, say="No longer following a player.", prefs={**clean, "follow": None})
        player, err = find_player(b, q)
        if err:
            return {**err, "hint": "ask which player"}
        return _ok(b, p, None, prefs={**clean, "follow": player["id"]},
                   say=f"Following {player['name']}: you'll hear a soft cue, and the name, when {player['last_name']} "
                       "is on the ball.")
    # SEAM(B->A): the relay publishes `prefs` to the listener's page; nothing here touches the match.
    if "detail" in clean:      # two levels since 27 Oct (D30): the page filters the track by cue priority
        return _ok(b, p, None, say=DETAIL_SAID[clean["detail"]], prefs=clean)
    if "verbosity" in prefs:   # an old or made-up level: name the two we have rather than "Done." for nothing
        return _ok(b, p, None, say=f"Done. {NO_DETAIL_LEVEL}" if clean else NO_DETAIL_LEVEL, prefs=clean)
    return _ok(b, p, [_static("done")], prefs=clean)


# The fan's sound groups on one 0..100 scale (0 = off), as the page's mixer shows them (web/src/audio/mix.ts SOUNDS).
SOUNDS = {"commentator": "The commentator", "crowd": "The crowd murmur", "chants": "The chants",
          "reactions": "The crowd reactions", "whistle": "The whistle", "passes": "The passes", "shots": "The shots",
          "tackles": "The tackles", "saves": "The saves", "net": "The ball in the net", "ball_ping": "The ball ping"}


def adjust_sound(b: Bundle, p: float, sound: Any = None, change: Any = None, level: Any = None,
                 current: Any = None) -> dict:
    """"Turn the whistle down by 5", "set the chants to 40". `current` is the page's level for `sound`, which the
    relay adds from the fan's last `ask` (never the model); without it the answer says the change, not the result."""
    if sound not in SOUNDS:
        return {"error": "unknown_sound", "candidates": list(SOUNDS)}
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)   # noqa: E731
    if num(level):
        new = round(min(100.0, max(0.0, float(level))))
    elif num(change) and change:
        step = round(min(100.0, max(-100.0, float(change))))
        if not num(current):
            word = "up" if step > 0 else "down"
            return _ok(b, p, None, say=f"{SOUNDS[sound]}, {word} by {abs(step)}.", prefs={"sound": sound, "change": step})
        new = round(min(100.0, max(0.0, float(current) + step)))
    else:
        return {"error": "bad_arguments", "candidates": [],
                "hint": "give change (-100..100, e.g. -5) or level (0..100)"}
    if num(current) and new == round(float(current)):
        edge = " That's off." if new == 0 else " That's the loudest." if new == 100 else ""
        say = f"{SOUNDS[sound]} is already at {new} out of 100.{edge}"
    else:
        say = f"{SOUNDS[sound]} is now {new} out of 100." if new else f"{SOUNDS[sound]} is now off."
    # SEAM(B->A): like set_preferences, the relay publishes `prefs` to the page; nothing here touches the match.
    return _ok(b, p, None, say=say, prefs={"sound": sound, "level": new})


# D27: the languages the commentator speaks: code -> (name, the Reds, Navy, a short confirmation in that language).
# commentary/languages.py pre-records the match in each; the relay switches the live voice and instructions.
LANGUAGES = {
    "en": ("English", "Reds", "Navy", "Commentary in English."),
    "bg": ("Bulgarian", "Червените", "Сините", "Коментарът продължава на български."),
    "es": ("Spanish", "los Rojos", "los Azules", "Seguimos la narración en español."),
    "ar": ("Arabic", "الحمر", "الزرق", "نواصل التعليق باللغة العربية."),
    "fr": ("French", "les Rouges", "les Bleus", "On continue le commentaire en français."),
    "de": ("German", "die Roten", "die Blauen", "Weiter geht's mit dem Kommentar auf Deutsch."),
    "hi": ("Hindi", "लाल टीम", "नीली टीम", "कमेंट्री अब हिंदी में जारी है।"),
}


def set_language(b: Bundle, p: float, language: Any = None) -> dict:
    """"Speak Bulgarian": the page switches the match commentary, the relay the live answers."""
    if language not in LANGUAGES:
        return {"error": "unknown_language", "candidates": list(LANGUAGES)}
    # SEAM(B->A): like set_preferences, the relay publishes `prefs` to the page; nothing here touches the match.
    return _ok(b, p, None, say=LANGUAGES[language][3], prefs={"language": language})


TOOLS = {f.__name__: f for f in (get_score_and_clock, get_ball_position, where_is, get_player_stats, get_last_events,
                                 explain_moment, what_did_i_miss, get_recap, set_preferences, adjust_sound,
                                 set_language)}


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
