"""The Q&A brain: tools, persona and no-LLM router for "ask the commentator".

OWNER: B (Nikolay). Stub created by A in Stage 0 with the API from TEAM_SPLIT.md "The seams" point 2.
From the merge of the Stage 0 PR on, only B edits this package. The API is append-only after Wed 21 Oct 18:00 Sofia.

No Microsoft imports here, ever. A's relay imports this module and hosts it inside Voice Live:
    from tely.qa import TOOL_SCHEMAS, PERSONA, call_tool, catch_up
The relay injects ``playhead_s`` from the session, so the model never sets the clock.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "TOOL_SCHEMAS",
    "PERSONA",
    "FRAGMENTS",
    "call_tool",
    "answer_text",
    "catch_up",
    "hold_that_thought",
]

# SEAM(A->B): A's relay sends these to Voice Live as-is ("function" tool format).
# Copied from stoynev research/43-tely-architecture.md §3 (6 lookups from file 40, 2 preference tools from file 36).
# None of them takes a clock argument: the relay supplies playhead_s to call_tool().
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "get_score_and_clock",
        "description": "Score and minute as the listener hears it now.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "get_ball_position",
        "description": "Which team has the ball and where, in spoken zone words. Also pings the ball sound.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "where_is",
        "description": "Where one player is now, relative to goal and ball.",
        "parameters": {
            "type": "object",
            "properties": {"player": {"type": "string", "description": "Name or shirt number as the fan said it"}},
            "required": ["player"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_player_stats",
        "description": "Verified stats for one player so far.",
        "parameters": {
            "type": "object",
            "properties": {
                "player": {"type": "string"},
                "metrics": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["distance_km", "top_speed_kmh", "passes", "shots"]},
                },
            },
            "required": ["player"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_last_events",
        "description": "Most recent events, newest first.",
        "parameters": {
            "type": "object",
            "properties": {"n": {"type": "integer", "minimum": 1, "maximum": 5}},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "explain_moment",
        "description": "Why a recent moment mattered (cached, verified). Use an id from get_last_events.",
        "parameters": {
            "type": "object",
            "properties": {"moment_id": {"type": "string"}},
            "required": ["moment_id"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "what_did_i_miss",
        "description": "Key events since a match time.",
        "parameters": {
            "type": "object",
            "properties": {"since": {"type": "string", "description": "mm:ss"}},
            "required": ["since"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "set_preferences",
        "description": "Change the crowd level or the vibration. The commentary has one level of detail: it can't be "
                       "made more or less detailed yet.",
        "parameters": {
            "type": "object",
            "properties": {
                "crowd_mix": {"type": "number", "minimum": 0, "maximum": 1},
                "haptics": {"type": "string", "enum": ["off", "events", "full"]},
            },
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "adjust_sound",
        "description": "Make one sound louder or quieter on the fan's 0 to 100 scale (0 is off). Use change for "
                       "\"down by 5\" or \"up by 10\", level for \"set it to 40\".",
        "parameters": {
            "type": "object",
            "properties": {
                "sound": {"type": "string", "enum": ["commentator", "crowd", "chants", "reactions", "whistle", "passes",
                                                     "shots", "tackles", "saves", "net", "ball_ping"]},
                "change": {"type": "integer", "minimum": -100, "maximum": 100},
                "level": {"type": "integer", "minimum": 0, "maximum": 100},
            },
            "required": ["sound"],
            "additionalProperties": False,
        },
    },
]

from .bundle import Bundle, load_bundle  # noqa: E402
from .fragments import FRAGMENTS  # noqa: E402,F401  (SEAM(B->A): A's answers.py renders every entry)
from .persona import PERSONA  # noqa: E402,F401  (SEAM(B->A): Voice Live session instructions)
from . import router, tools  # noqa: E402

_DEFAULT: Bundle | None = None


def _bundle(bundle: Any) -> Bundle:
    """`bundle` from the caller, or the judge cut loaded once (the relay may pass None)."""
    global _DEFAULT
    if isinstance(bundle, Bundle):
        return bundle
    if _DEFAULT is None:
        _DEFAULT = load_bundle()
    return _DEFAULT


def call_tool(name: str, args: dict[str, Any], *, playhead_s: float, bundle: Any) -> dict[str, Any]:
    """Run one tool at the listener's playhead.

    Returns ``{say, evidence_ids, as_of_clock}`` or ``{error, candidates}``. Never reads past ``playhead_s``.
    (Also ``fragments``: the FRAGMENTS ids that speak ``say`` offline, or None.)
    """
    # SEAM(A->B): the relay calls this for every Voice Live function call, with playhead_s from the session.
    return tools.call(name, args, playhead_s, _bundle(bundle))


def answer_text(question: str, *, playhead_s: float, bundle: Any) -> dict[str, Any]:
    """Deterministic keyword/intent router with no LLM: the offline fallback and the preset-question engine."""
    return router.answer_text(question, playhead_s=playhead_s, bundle=_bundle(bundle))


def catch_up(since_s: float, until_s: float, bundle: Any) -> str:
    """Spoken summary of the key events in ``[since_s, until_s]``."""
    # SEAM(A->B): the relay calls this when a listener comes back after a pause.
    return tools.catch_up_answer(_bundle(bundle), since_s, until_s)["say"]


HOLD_LOOKAHEAD_S = 8.0   # a build-up line plays 4 s before a shot (file 39 LEAD_S); "due within 4 s" -> shot within 8 s
HOLD_MIN_XG = 0.08       # file 39: the planner builds up only for chances with xG >= 0.08


def hold_that_thought(playhead_s: float, bundle: Any) -> bool:
    """True if something is about to happen, so the answer should wait. Says THAT, never WHAT."""
    b = _bundle(bundle)
    p = b.clamp(playhead_s)
    return any(e["type"] == "shot" and p < b.sig(e["id"])["t"] <= p + HOLD_LOOKAHEAD_S
               and (b.sig(e["id"])["xg"] or 0) >= HOLD_MIN_XG for e in b.events)
