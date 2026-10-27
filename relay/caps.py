"""Abuse and cost caps for the live Ask.

WHY (file 21 "Request floods", "Bad day"): Container Apps has no per-IP limiter, so the relay keeps in-memory counters.
They are exact while there is one replica; with maxReplicas 2 each replica counts on its own, so the real ceiling is
at most twice these numbers. Budgets don't stop spending (file 21), so these caps are the brake.
Numbers are ours (file 40 §6), not from any doc:
- 30 questions per session, 4 tool calls per answer, close after 90 s idle, a fresh Voice Live connection after 55 min
  (the service allows 60, file 40 §2);
- a global daily question cap (about $0.02 per question, file 40 §6: 200 a day is about $4 a day);
- per IP: 6 new sessions per 10 minutes, at most 2 open at once (one fan, plus a second tab or a NAT neighbour).
DEMO_MODE is read on every call, so `az containerapp update --set-env-vars DEMO_MODE=off` turns live Ask off.
"""
from __future__ import annotations

import collections
import os
import time
from dataclasses import dataclass, field
from typing import Callable


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass
class Caps:
    questions_per_session: int = 30
    tool_calls_per_answer: int = 4
    idle_s: float = 90.0
    reconnect_after_s: float = 55 * 60.0
    max_listen_s: float = 12.0
    sessions_per_ip: int = 6
    sessions_window_s: float = 600.0
    open_per_ip: int = 2
    daily_questions: int = field(default_factory=lambda: _int("DAILY_QUESTION_CAP", 200))
    clock: Callable[[], float] = time.time
    _opened: dict[str, collections.deque] = field(default_factory=lambda: collections.defaultdict(collections.deque))
    _open: collections.Counter = field(default_factory=collections.Counter)
    _day: str = ""
    _today: int = 0

    @staticmethod
    def mode() -> str:
        return os.environ.get("DEMO_MODE", "live").strip().lower()

    def mode_refusal(self) -> str | None:
        return None if self.mode() == "live" else "demo_off"

    def open_session(self, ip: str) -> str | None:
        """Count a new live session for ip, or say why not."""
        if (r := self.mode_refusal()) or (r := self._day_refusal()):
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
        return None

    def close_session(self, ip: str) -> None:
        if self._open[ip] > 0:
            self._open[ip] -= 1

    def question(self, asked_in_session: int) -> str | None:
        """Count one question, or say why not. `asked_in_session` is how many this session already asked."""
        if (r := self.mode_refusal()) or (r := self._day_refusal()):
            return r
        if asked_in_session >= self.questions_per_session:
            return "session_cap"
        self._today += 1
        return None

    def _day_refusal(self) -> str | None:
        day = time.strftime("%Y-%m-%d", time.gmtime(self.clock()))
        if day != self._day:
            self._day, self._today = day, 0
        return "daily_cap" if self._today >= self.daily_questions else None
