"""The Q&A brain: tools, persona and no-LLM router for "ask the commentator".

OWNER: B (Nikolay). Stub created by A in Stage 0 with the API from TEAM_SPLIT.md "The seams" point 2.
From the merge of the Stage 0 PR on, only B edits this package. The API is append-only after Wed 21 Oct 18:00 Sofia.

No Microsoft imports here, ever. A's relay imports this module and hosts it inside Voice Live:
    from audiostands.qa import TOOL_SCHEMAS, PERSONA, call_tool, catch_up
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
# Copied from stoynev research/43-audio-stands-architecture.md §3 (6 lookups from file 40, 2 preference tools from file 36).
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
        "description": "Change verbosity, crowd mix or vibration.",
        "parameters": {
            "type": "object",
            "properties": {
                "verbosity": {"type": "string", "enum": ["describer", "radio", "calm"]},
                "crowd_mix": {"type": "number", "minimum": 0, "maximum": 1},
                "haptics": {"type": "string", "enum": ["off", "events", "full"]},
            },
            "additionalProperties": False,
        },
    },
]

# SEAM(A->B): A's relay sends this as the Voice Live session instructions. B writes it (file 40 §4 and §6).
PERSONA: str = ""  # TODO(B): Role, Tone, Tools, Scope; 1-2 sentences; never say what happens next; no betting advice.

# SEAM(A->B): every fixed phrase that needs audio, as [{"id": str, "text": str}]. A's answers.py renders each with Azure TTS.
FRAGMENTS: list[dict[str, str]] = []  # TODO(B): due Sat 24 Oct 14:00 (TEAM_SPLIT.md timeline).


def call_tool(name: str, args: dict[str, Any], *, playhead_s: float, bundle: Any) -> dict[str, Any]:
    """Run one tool at the listener's playhead.

    Returns ``{say, evidence_ids, as_of_clock}`` or ``{error, candidates}``. Never reads past ``playhead_s``.
    """
    # SEAM(A->B): the relay calls this for every Voice Live function call, with playhead_s from the session.
    raise NotImplementedError("B implements call_tool (Stage 7, TEAM_SPLIT.md seam 2)")


def answer_text(question: str, *, playhead_s: float, bundle: Any) -> dict[str, Any]:
    """Deterministic keyword/intent router with no LLM: the offline fallback and the preset-question engine."""
    raise NotImplementedError("B implements answer_text (Stage 6/7, TEAM_SPLIT.md seam 2)")


def catch_up(since_s: float, until_s: float, bundle: Any) -> str:
    """Spoken summary of the key events in ``[since_s, until_s]``."""
    # SEAM(A->B): the relay calls this when a listener comes back after a pause.
    raise NotImplementedError("B implements catch_up (TEAM_SPLIT.md seam 2)")


def hold_that_thought(playhead_s: float, bundle: Any) -> bool:
    """True if something is about to happen, so the answer should wait. Says THAT, never WHAT."""
    raise NotImplementedError("B implements hold_that_thought (TEAM_SPLIT.md seam 2)")
