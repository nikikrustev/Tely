"""POST /feedback: tester-mode answers and problem reports (web/src/tester/, D19). OWNER: A (potencialbg).

One small, flat JSON object per request. Every key must be in SCHEMA (no free-form keys), every value is checked
against its type, range or choice list, and free text is trimmed and capped. The result is one Application Insights
custom event "tester_feedback" (telemetry.py). The client IP is used only for the in-memory rate limit and is never
part of the event.
"""
from __future__ import annotations

import collections
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

MAX_BYTES = 4096            # the whole body; the browser trims text to fit (web/src/tester/payload.ts)
TEXT_MAX = 500              # characters per free-text field, after trimming

# kind: what the tester just finished. consent (welcome screen), task (Done/Skip on a task), clip (questions after
# a clip), ask / settings (tasks 6-7), overall (task 8), problem ("Report a problem").
_E = lambda *xs: ("enum", frozenset(xs))   # noqa: E731
_I = lambda lo, hi: ("int", lo, hi)        # noqa: E731
_B = ("bool",)
_T = ("text", TEXT_MAX)
SETTINGS = ("club", "crowd", "haptics", "strength", "calibrate", "radar")
SCHEMA: dict[str, tuple] = {
    "v": _I(1, 1),
    "kind": _E("consent", "task", "clip", "ask", "settings", "overall", "problem"),
    "tester": ("re", re.compile(r"t-[0-9a-f]{8}")),
    "eid": ("re", re.compile(r"[0-9a-f]{8}")),           # per event, so a retried event is counted once
    "group": _E("A", "B"),
    "consent_take_part": _B, "consent_quote": _B,
    "task": _I(1, 8), "result": _E("done", "skip"),
    # questions after a clip (eval/listening_test.md sections 5 and 6); *_ok is the browser's score against the key
    "clip": _I(1, 2),
    "where": _E("left_close", "right_close", "left_far", "right_far", "middle", "dont_know"),
    "side": _E("near", "far", "middle", "dont_know"),
    "danger": _E("reds", "navy", "both", "no", "dont_know"),
    "scored": _E("reds", "navy", "nobody", "dont_know"),
    "where_ok": _I(0, 1), "side_ok": _I(0, 1), "danger_ok": _I(0, 1), "scored_ok": _I(0, 1),
    "enjoy": _I(1, 5), "access": _I(1, 5), "follow": _I(1, 5),
    # tasks 6 and 7
    "ask_presets": _I(0, 99), "ask_live_available": _B, "ask_live_tried": _B,
    "ask_worked": _E("yes", "partly", "no", "not_tried"),
    "settings_changed": ("re", re.compile(rf"(?:{'|'.join(SETTINGS)})(?:,(?:{'|'.join(SETTINGS)}))*")),
    "settings_easy": _E("yes", "partly", "no"),
    # overall feedback
    "confusing": _T, "liked": _T, "would_use": _T,
    "preferred": _E("1", "2", "none"),
    "device": _E("android_phone", "iphone", "windows", "mac", "tablet", "other"),
    "headphones": _E("wired", "bluetooth", "none"),
    "screen_reader": _E("none", "nvda", "jaws", "narrator", "voiceover", "talkback", "other"),
    "sight": _E("sighted", "partially_sighted", "blind", "not_said"),
    # "Report a problem" and the context the browser attaches to it (user-agent family only, never the full string)
    "problem_kind": _E("sound", "voice", "controls", "confusing", "stuck", "other"),
    "problem_text": _T,
    "ctx_task": _I(0, 8), "ctx_playhead": ("num", 0.0, 10_000.0), "ctx_playing": _B,
    "ctx_club": _E("H", "A"), "ctx_crowd": _I(0, 100), "ctx_haptics": _E("off", "events", "full"),
    "ctx_browser": _E("chrome", "edge", "firefox", "safari", "samsung", "opera", "other"),
    "ctx_os": _E("windows", "android", "ios", "macos", "linux", "chromeos", "other"),
    "ctx_viewport": ("re", re.compile(r"\d{2,5}x\d{2,5}")),
    "ctx_relay": _B,
}
REQUIRED = ("v", "kind", "tester", "eid")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class Invalid(ValueError):
    pass


def validate(obj: Any) -> dict[str, str]:
    """A checked event as flat string properties (App Insights customDimensions are strings), or Invalid."""
    if not isinstance(obj, dict):
        raise Invalid("not an object")
    unknown = sorted(k for k in obj if k not in SCHEMA)
    if unknown:
        raise Invalid(f"unknown keys: {', '.join(unknown[:5])}")
    missing = [k for k in REQUIRED if k not in obj]
    if missing:
        raise Invalid(f"missing: {', '.join(missing)}")
    out: dict[str, str] = {}
    for k, v in obj.items():
        if v is None:
            continue
        rule = SCHEMA[k]
        kind = rule[0]
        if kind == "enum":
            if not isinstance(v, str) or v not in rule[1]:
                raise Invalid(f"{k}: not an allowed value")
            out[k] = v
        elif kind == "int":
            if isinstance(v, bool) or not isinstance(v, int) or not rule[1] <= v <= rule[2]:
                raise Invalid(f"{k}: expected a whole number {rule[1]}-{rule[2]}")
            out[k] = str(v)
        elif kind == "num":
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not rule[1] <= v <= rule[2]:
                raise Invalid(f"{k}: expected a number {rule[1]:g}-{rule[2]:g}")
            out[k] = f"{float(v):.1f}"
        elif kind == "bool":
            if not isinstance(v, bool):
                raise Invalid(f"{k}: expected true or false")
            out[k] = "true" if v else "false"
        elif kind == "re":
            if not isinstance(v, str) or not rule[1].fullmatch(v):
                raise Invalid(f"{k}: bad format")
            out[k] = v
        else:  # text
            if not isinstance(v, str):
                raise Invalid(f"{k}: expected text")
            t = _CONTROL.sub("", v).strip()[: rule[1]].strip()
            if t:
                out[k] = t
    return out


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass
class FeedbackCaps:
    """D17-style brakes (ours): per IP 60 events per 10 min (a tester sends about 15, a shared home Wi-Fi a few
    testers), and a global daily cap. In memory, per replica, so with maxReplicas 2 the ceiling is at most twice."""
    per_ip: int = 60
    window_s: float = 600.0
    daily: int = field(default_factory=lambda: _int("DAILY_FEEDBACK_CAP", 3000))
    clock: Callable[[], float] = time.time
    _hits: dict[str, collections.deque] = field(default_factory=lambda: collections.defaultdict(collections.deque))
    _day: str = ""
    _today: int = 0

    def allow(self, ip: str) -> str | None:
        """Count one event from ip, or say why not ("rate_limit" | "daily_cap")."""
        now = self.clock()
        day = time.strftime("%Y-%m-%d", time.gmtime(now))
        if day != self._day:
            self._day, self._today = day, 0
        if self._today >= self.daily:
            return "daily_cap"
        q = self._hits[ip]
        while q and q[0] <= now - self.window_s:
            q.popleft()
        if len(q) >= self.per_ip:
            return "rate_limit"
        q.append(now)
        if len(self._hits) > 5000:            # forget IPs whose window has passed, so the dict can't grow forever
            for k in [k for k, d in self._hits.items() if d[-1] <= now - self.window_s]:
                del self._hits[k]
        self._today += 1
        return None
