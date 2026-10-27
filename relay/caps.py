"""Abuse and cost caps for the live Ask.

WHY (file 21 "Request floods", "Bad day"): Container Apps has no per-IP limiter, so the relay keeps in-memory counters.
They are exact while there is one replica; with maxReplicas 2 each replica counts on its own, so the real ceiling is
at most twice these numbers. They also start again from zero when the relay scales from zero (D6). Budgets don't stop
spending (file 21), so these caps are the brake.
Numbers are ours (file 40 §6), not from any doc:
- 30 questions per session, 4 tool calls per answer, close after 90 s idle, a fresh Voice Live connection after 55 min
  (the service allows 60, file 40 §2);
- a session lasts at most 10 minutes, whatever the idle timer says, and sends at most ~2 minutes of mic audio;
- the relay ends a turn itself 12 s (+ 3 s grace) after the fan starts talking, if the browser hasn't;
- a global daily question cap (about $0.02 per question, file 40 §6: 200 a day is about $4 a day), and 20 a day per IP;
  a question counts once Voice Live has heard it (a transcript or a response), not when the `ask` arrives;
- per IP: 6 new sessions per 10 minutes, at most 2 open at once (one fan, plus a second tab or a NAT neighbour).
DEMO_MODE is read on every call, so `az containerapp update --set-env-vars DEMO_MODE=off` turns live Ask off.
"""
from __future__ import annotations

import collections
import os
import time
from dataclasses import dataclass, field
from typing import Callable

PRUNE_ABOVE = 5000          # IPs kept before old ones are forgotten (feedback.py does the same)


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _prune(hits: dict[str, collections.deque], older_than: float, keep: Callable[[str], bool] = lambda _: False,
           above: int = PRUNE_ABOVE) -> None:
    """Forget IPs whose window has passed, so the dict can't grow forever."""
    if len(hits) > above:
        for k in [k for k, d in hits.items() if (not d or d[-1] <= older_than) and not keep(k)]:
            del hits[k]


@dataclass
class Caps:
    questions_per_session: int = 30
    tool_calls_per_answer: int = 4
    idle_s: float = 90.0
    session_max_s: float = 600.0                 # hard: idle-timer resets can't extend it
    reconnect_after_s: float = 55 * 60.0
    max_listen_s: float = 12.0                   # web/src/voice/live-ask.ts MAX_LISTEN_MS, from speech_started
    listen_grace_s: float = 3.0                  # the relay's own commit comes this much later (a backstop)
    audio_bytes_per_session: int = 120 * 48000   # ~2 min of PCM16 24 kHz mono (48 kB/s)
    sessions_per_ip: int = 6
    sessions_window_s: float = 600.0
    open_per_ip: int = 2
    daily_questions: int = field(default_factory=lambda: _int("DAILY_QUESTION_CAP", 200))
    daily_questions_per_ip: int = field(default_factory=lambda: _int("DAILY_QUESTION_CAP_PER_IP", 20))
    prune_above: int = PRUNE_ABOVE
    clock: Callable[[], float] = time.time
    _opened: dict[str, collections.deque] = field(default_factory=lambda: collections.defaultdict(collections.deque))
    _open: collections.Counter = field(default_factory=collections.Counter)
    _day: str = ""
    _today: int = 0
    _ip_today: collections.Counter = field(default_factory=collections.Counter)

    @staticmethod
    def mode() -> str:
        return os.environ.get("DEMO_MODE", "live").strip().lower()

    def mode_refusal(self) -> str | None:
        return None if self.mode() == "live" else "demo_off"

    def open_session(self, ip: str) -> str | None:
        """Count a new live session for ip, or say why not."""
        if (r := self.mode_refusal()) or (r := self._day_refusal(ip)):
            return r
        now, q = self.clock(), self._opened[ip]
        while q and q[0] <= now - self.sessions_window_s:
            q.popleft()
        if len(q) >= self.sessions_per_ip:
            return "rate_limit"
        if self._open[ip] >= self.open_per_ip:
            return "busy"
        q.append(now)
        self._open[ip] += 1
        _prune(self._opened, now - self.sessions_window_s, keep=lambda k: self._open[k] > 0, above=self.prune_above)
        return None

    def close_session(self, ip: str) -> None:
        if self._open[ip] > 1:
            self._open[ip] -= 1
        else:
            self._open.pop(ip, None)          # a Counter keeps zero entries; drop them

    def question(self, asked_in_session: int, ip: str = "?") -> str | None:
        """May this session ask one more question? `asked_in_session` is how many it already asked. Counts nothing:
        count_question() does, once Voice Live has heard the question."""
        if (r := self.mode_refusal()) or (r := self._day_refusal(ip)):
            return r
        if asked_in_session >= self.questions_per_session:
            return "session_cap"
        return None

    def count_question(self, ip: str = "?") -> None:
        """One question reached Voice Live (a transcript or a response): count it against today's caps."""
        self._day_refusal(ip)                 # rolls the day over first
        self._today += 1
        self._ip_today[ip] += 1

    def _day_refusal(self, ip: str) -> str | None:
        day = time.strftime("%Y-%m-%d", time.gmtime(self.clock()))
        if day != self._day:
            self._day, self._today = day, 0
            self._ip_today.clear()            # the per-IP counts last a day, so the new day empties them
        if self._today >= self.daily_questions or self._ip_today[ip] >= self.daily_questions_per_ip:
            return "daily_cap"
        return None


@dataclass
class RateLimit:
    """At most `per_ip` hits per IP in a sliding `window_s` (POST /mcp: 60 a minute, ours; the MCP spec says servers
    "MUST ... rate limit tool invocations", file 40 §3). Forgets IPs whose window has passed."""
    per_ip: int = 60
    window_s: float = 60.0
    prune_above: int = PRUNE_ABOVE
    clock: Callable[[], float] = time.time
    _hits: dict[str, collections.deque] = field(default_factory=lambda: collections.defaultdict(collections.deque))

    def allow(self, ip: str) -> bool:
        now, q = self.clock(), self._hits[ip]
        while q and q[0] <= now - self.window_s:
            q.popleft()
        if len(q) >= self.per_ip:
            return False
        q.append(now)
        _prune(self._hits, now - self.window_s, above=self.prune_above)
        return True
