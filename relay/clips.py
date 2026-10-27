"""Fixed lines the live Ask says when it can't take a question.

Each one is pre-rendered in the commentary voice (relay/render_clips.py -> web/public/replay/v1/judge/live/), so a
refusal still sounds like the commentator, and the browser can play the "unavailable" line even when the relay is down.
Every line ends by pointing at the preset questions, because that is where the fan lands next.
"""
from __future__ import annotations

CLIPS: dict[str, str] = {
    "live_unavailable": "Live questions aren't available right now, so here are the preset questions.",
    "live_not_heard": "I didn't catch a question, so here are the preset questions.",
    "live_session_cap": "That's all the live questions for this visit. The preset questions still work.",
    "live_daily_cap": "Live questions are resting for today. The preset questions still work.",
    "live_rate_limit": "Lots of live questions at once. Here are the preset questions for now.",
}

# Not refusals: what the browser says while it is still trying (voice/live-ask.ts WAKING, the cold-relay retry).
NOTICES: dict[str, str] = {
    "live_waking": "Waking up the live commentator, one moment.",
}

# Refusal reason (caps.py, app.py) -> the clip that explains it.
REASON_CLIP: dict[str, str] = {
    "demo_off": "live_unavailable",
    "unavailable": "live_unavailable",
    "not_heard": "live_not_heard",
    "session_cap": "live_session_cap",
    "daily_cap": "live_daily_cap",
    "rate_limit": "live_rate_limit",
    "busy": "live_rate_limit",
}


def refusal(reason: str) -> dict[str, str]:
    """The spoken refusal the browser plays: {type, reason, clip, say}. Unknown reasons say "unavailable"."""
    clip = REASON_CLIP.get(reason, "live_unavailable")
    return {"type": "refusal", "reason": reason, "clip": clip, "say": CLIPS[clip]}
