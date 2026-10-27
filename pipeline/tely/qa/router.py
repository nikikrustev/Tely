"""answer_text(): a keyword/intent router with no LLM. OWNER: B (Nikolay).

It is the offline fallback when the live voice is unavailable, the engine behind the preset questions, and a cheap
test harness for the tools. Order matters: refusals (predictions, betting) are checked before lookups, so "who will
score next" never reaches a tool.
"""
from __future__ import annotations

import re

from .bundle import Bundle
from .fragments import STATIC
from . import tools

RULES: list[tuple[str, re.Pattern]] = [
    ("no_spoilers", re.compile(r"\b(who (will|is going to|gonna)|will (they|we|\w+) (win|score|lose)|scores? next|next goal"
                               r"|predict|what happens next|going to happen|final score|who wins"
                               r"|(is|are) (there )?(a |another )?(goal|chance|shot|something)s? (coming|about to)"
                               r"|will there be|are (they|we) going to|about to (score|happen))\b")),
    ("no_betting", re.compile(r"\b(bet|bets|betting|odds|gambl\w*|wager|bookie\w*)\b")),
    ("recap", re.compile(r"\b(recap|sum (it )?up|summary|summari[sz]e|story so far|so far|half[- ]?time|full[- ]?time)\b")),
    ("missed", re.compile(r"\b(miss|missed|catch (me )?up|while i was|i was away)\b")),
    ("last", re.compile(r"\b(what (just )?happened|just now|last (event|thing|play)|recent|replay)\b")),
    ("stats", re.compile(r"\b(stats?|statistics|how (far|fast|many)|passes|distance|top speed|run)\b")),
    ("ball", re.compile(r"\b(ball|who has it|who'?s got it|possession|which side|where('s| is) (the )?play)\b")),
    ("where_is", re.compile(r"\bwhere('s| is)\b")),
    ("score", re.compile(r"\b(score|scores|winning|losing|ahead|result|minute|time|clock|how long)\b")),
]
FOOTBALL = re.compile(r"\b(reds?|navy|goal|keeper|player|team|match|game|shot|pass|foul|card|var|referee|number)\b")


def _player_query(q: str) -> str:
    m = re.search(r"\b(?:where(?:'s| is)|stats? (?:for|of)?|how (?:far|fast|many \w+) (?:has|did|is)?)\s+(.+?)\??$", q)
    return (m.group(1) if m else q).replace("number", "").strip()


def route(question: str) -> str:
    q = question.lower().strip()
    for intent, rx in RULES:
        if rx.search(q):
            return intent
    return "not_sure" if FOOTBALL.search(q) else "off_topic"


def answer_text(question: str, *, playhead_s: float, bundle: Bundle) -> dict:
    p = bundle.clamp(playhead_s)
    intent = route(question)
    q = question.lower().strip()
    if intent in ("no_spoilers", "no_betting", "off_topic", "not_sure"):
        res = {"say": STATIC[intent], "evidence_ids": [], "as_of_clock": bundle.clock_str(p), "fragments": [intent]}
    elif intent == "score":
        res = tools.call("get_score_and_clock", {}, p, bundle)
    elif intent == "ball":
        res = tools.call("get_ball_position", {}, p, bundle)
    elif intent == "last":
        res = tools.call("get_last_events", {"n": 2}, p, bundle)
    elif intent == "recap":
        res = tools.call("get_recap", {"moment": "so_far"}, p, bundle)
    elif intent == "missed":
        res = tools.call("what_did_i_miss", {"since": bundle.clock_str(max(bundle.t0, p - 120))}, p, bundle)
    elif intent == "stats":
        res = tools.call("get_player_stats", {"player": _player_query(q)}, p, bundle)
    else:  # where_is
        res = tools.call("where_is", {"player": _player_query(q)}, p, bundle)
    if "error" in res:   # spoken fallback for a player we couldn't pin down
        names = ", ".join(res.get("candidates", [])[:3])
        res = {"say": f"Which player? For example: {names}." if names else STATIC["not_sure"], "evidence_ids": [],
               "as_of_clock": bundle.clock_str(p), "fragments": None if names else ["not_sure"], "candidates": res.get("candidates", [])}
    return {**res, "intent": intent}
