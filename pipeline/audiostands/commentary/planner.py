"""Look-ahead planner over the window [P, P + D] (file 39 planner; file 43 §2 timing). OWNER: A (potencialbg).

1. Every event becomes zero or more Drafts (templates.py).
2. Highest priority claims its slot first; a line may slide later in 100 ms steps up to its stale_s, trying shorter
   fallback texts before it is dropped. Outcome lines go first, then build-ups, so the build-up always fits before
   its reveal.
3. Routine passes fill the gaps only with breathing room around them (Radio level: ball and key moments, short pauses).
   Nothing but the shot's own lines may talk between a build-up and its reveal (the hush keeps the rise unbroken).
4. Quiet fill: never more than MAX_QUIET_S between line starts without spoken state (file 39 §3).

Durations come from duration_of(text, style, pause_ms): real MP3 durations once rendered, an estimate before that.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from audiostands.commentary import templates as T
from audiostands.commentary.source import Match

WPS = 2.6            # words per second (file 39); our probe on 21 Oct measured ~2.6 for Andrew HD
ELLIPSIS_S = 0.3     # "..." is spoken as a short pause (our estimate)
MIN_GAP_S = 0.4      # silence between two lines (file 39)
MAX_QUIET_S = 20.0   # max time between line starts without spoken state (file 39 §3, our guess)
FILL_AFTER_S = 6.0   # a quiet fill comes this long after the last line ends, unless MAX_QUIET_S forces it sooner
ROUTINE_GAP_S = 1.5  # a routine pass is described only after this much silence
HUSHED = ("describe", "state")  # kinds that may not talk over a build-up (build start -> reveal)
STEP_S = 0.1
EPS = 1e-6           # float tolerance for the overlap test (15.05 + 0.4 > 15.45 in floats)

DurationFn = Callable[[str, str, int], float]


@dataclass
class Line:
    draft: T.Draft
    text: str
    t_in: float
    dur: float

    @property
    def end(self) -> float:
        return self.t_in + self.dur


def estimate(text: str, style: str, pause_ms: int) -> float:
    return len(text.split()) / WPS + text.count("...") * ELLIPSIS_S + pause_ms / 1000


def drafts(m: Match) -> list[T.Draft]:
    out = [T.intro(m)]
    for e in m.events:
        if e.get("sub_type") == "kick_off" and m.t(e) <= m.t_start + 1:
            continue  # the intro says who kicks off
        if e["type"] == "shot":
            out += [T.build(m, e), T.call(m, e), T.react(m, e), T.detail(m, e)]
        else:
            out.append(T.describe(m, e))  # saves are spoken by the shot's react line
    return [d for d in out if d is not None and m.t_start <= d.t < m.t_end]


def plan(m: Match, duration_of: DurationFn = estimate) -> list[Line]:
    placed: list[Line] = []

    def place(d: T.Draft, gap_before: float = MIN_GAP_S) -> None:
        for text in d.texts:
            dur = duration_of(text, d.style, d.pause_ms)
            for k in range(int(round(d.stale_s / STEP_S)) + 1):
                a = round(d.t + STEP_S * k, 2)
                if _free(m, placed, a, a + dur, d.kind, gap_before):
                    placed.append(Line(d, text, a, dur))
                    return

    ds = drafts(m)
    for d in sorted((d for d in ds if d.prio > 0), key=lambda d: (-d.prio, d.t)):
        place(d)
    for d in sorted((d for d in ds if d.prio == 0), key=lambda d: d.t):
        place(d, gap_before=ROUTINE_GAP_S)
    placed.sort(key=lambda p: p.t_in)
    return _quiet_fill(m, placed, duration_of)


def _ceil2(t: float) -> float:
    return math.ceil(t * 100 - 1e-9) / 100


def _hushes(m: Match, placed: list[Line]) -> list[tuple[float, float]]:
    return [(p.t_in, m.reveal_t(m.by_id(p.draft.evidence[0]))) for p in placed if p.draft.kind == "build"]


def _free(m: Match, placed: list[Line], a: float, b: float, kind: str, gap_before: float = MIN_GAP_S) -> bool:
    if a < m.t_start - EPS or b > m.t_end + EPS:
        return False
    if kind in HUSHED and any(a < h1 and b > h0 for h0, h1 in _hushes(m, placed)):
        return False
    return all(b + MIN_GAP_S <= p.t_in + EPS or a + EPS >= p.end + gap_before for p in placed)


def _quiet_fill(m: Match, placed: list[Line], duration_of: DurationFn) -> list[Line]:
    out: list[Line] = []
    prev_start, prev_end, n = m.t_start, m.t_start - MIN_GAP_S, 0
    for nxt in [*placed, None]:
        limit = nxt.t_in if nxt else m.t_end
        while limit - prev_start > MAX_QUIET_S:
            # Preferred: FILL_AFTER_S after the last line. If that doesn't fit before the next line, as early as allowed.
            early = _ceil2(prev_end + MIN_GAP_S)  # round up: rounding down would land inside the gap
            pref = _ceil2(max(early, min(prev_end + FILL_AFTER_S, prev_start + MAX_QUIET_S)))
            fit = None
            for a in dict.fromkeys((pref, early)):
                d = T.state(m, a, n)
                for text in d.texts:
                    dur = duration_of(text, d.style, d.pause_ms)
                    if a + dur + (MIN_GAP_S if nxt else 0) <= limit and _free(m, placed, a, a + dur, "state"):
                        fit = Line(d, text, a, dur)
                        break
                if fit:
                    break
            if fit is None:
                break
            n += 1
            out.append(fit)
            prev_start, prev_end = fit.t_in, fit.end
        if nxt:
            out.append(nxt)
            prev_start, prev_end = nxt.t_in, max(prev_end, nxt.end)
    return out
