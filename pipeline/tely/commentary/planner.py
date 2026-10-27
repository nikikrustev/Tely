"""Look-ahead planner over the window [P, P + D] (file 39 planner; file 43 §2 timing). OWNER: A (potencialbg).

1. Every event becomes zero or more Drafts (templates.py).
2. Highest priority claims its slot first; a line may slide later in 100 ms steps up to its stale_s, trying shorter
   fallback texts before it is dropped. Outcome lines go first, then build-ups, so the build-up always fits before
   its reveal.
3. Routine passes fill the gaps only with breathing room around them (Radio level: ball and key moments, short pauses).
   Nothing but the shot's own lines may talk between a build-up and its reveal (the hush keeps the rise unbroken).
4. Ball fill: while the ball is in play, a short ball-first line ("Midfield, far side, Reds. It's with Ashski.")
   whenever BALL_EVERY_S passes without a line start, so no in-play stretch is quiet for more than MAX_BALL_QUIET_S
   (file 36 rule 1; Nikolay's listening note on PR #11). Dead-ball stoppages are left to step 5.
5. Quiet fill: never more than MAX_QUIET_S between line starts without spoken state (file 39 §3).

Durations come from duration_of(text, style, pause_ms): real MP3 durations once rendered, an estimate before that.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Callable

from tely.commentary import lively
from tely.commentary import templates as T
from tely.commentary.source import Match

STYLES = {"radio_v1": T, "lively": lively}


def lines_for(m: Match):
    """The template set for this match: radio_v1 unless build_commentary --style set m.style."""
    return STYLES[getattr(m, "style", "radio_v1")]

WPS = 2.6            # words per second (file 39); our probe on 21 Oct measured ~2.6 for Andrew HD
ELLIPSIS_S = 0.3     # "..." is spoken as a short pause (our estimate)
MIN_GAP_S = 0.4      # silence between two lines (file 39)
MAX_QUIET_S = 20.0   # max time between line starts without spoken state (file 39 §3, our guess)
FILL_AFTER_S = 6.0   # a quiet fill comes this long after the last line ends, unless MAX_QUIET_S forces it sooner
ROUTINE_GAP_S = 1.5  # a routine pass is described only after this much silence
BALL_EVERY_S = 9.0   # in play, a ball line once this long passes without a line start (#11 note: 8-10 s)
MAX_BALL_QUIET_S = 10.0  # longest in-play stretch without a line start; the tests hold the judge cut to it
BALL_GAP_S = 1.5     # silence either side of a ball line, so the crowd swells back between lines
SCORE_EVERY_S = 60.0 # a ball line may give the score instead of a name already heard, if not said this recently
DUCK_S = 0.6         # the crowd ducks 0.25 s before a line and releases 0.35 s after it (D12): the tightest ball gap
HUSHED = ("describe", "state", "kits", "ball")  # kinds that may not talk over a build-up (build start -> reveal)
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


def drafts(m: Match, plans: dict | None = None) -> list[T.Draft]:
    """plans: shot id -> the Director's verified tension plan (Stage 5). A shot without one uses the Stage 3 rules."""
    plans = plans or {}
    L = lines_for(m)
    out = [L.opener(m), L.kits(m)]
    for e in m.events:
        if e.get("sub_type") == "kick_off" and m.t(e) <= m.t_start + 1:
            continue  # the opener says who kicks off
        if e["type"] == "shot":
            out += [L.build(m, e, plans.get(e["id"])), L.call(m, e), L.react(m, e), L.detail(m, e)]
        elif e["type"] == "referee":
            out += L.var_check(m, e) if e.get("sub_type") == "var_check" else []
        elif e["type"] == "misc":
            out.append(L.foul(m, e))
        else:
            out.append(L.describe(m, e))  # saves and blocks are spoken by the shot's react line
    return [d for d in out if d is not None and m.t_start <= d.t < m.t_end]


def plan(m: Match, duration_of: DurationFn = estimate, plans: dict | None = None) -> list[Line]:
    placed: list[Line] = []

    def place(d: T.Draft, gap_before: float = MIN_GAP_S) -> None:
        # A build-up's hold (the Director's hold_ms) is dropped before its words are: each text is tried with the
        # hold, then without it, and only then the next, shorter text.
        held = (d, replace(d, pause_ms=0)) if d.kind == "build" and d.pause_ms else (d,)
        # A build-up should end by its shot, so the call ("Fenford, the header!") at shot + 0.2 s can still be heard
        # (file 39). Only if no text fits that way does it run on (BUILD_PLAN: never cut the build-up).
        shot_t = m.t(m.by_id(d.evidence[0])) if d.kind == "build" else None
        for by_shot in ((True, False) if shot_t is not None else (False,)):
            for text in d.texts:
                for dd in held:
                    dur = duration_of(text, dd.style, dd.pause_ms)
                    for k in range(int(round(dd.stale_s / STEP_S)) + 1):
                        a = round(dd.t + STEP_S * k, 2)
                        if by_shot and a + dur > shot_t + EPS:
                            break
                        if _free(m, placed, a, a + dur, dd.kind, gap_before):
                            placed.append(Line(dd, text, a, dur))
                            return

    ds = drafts(m, plans)
    for d in sorted((d for d in ds if d.prio > 0), key=lambda d: (-d.prio, d.t)):
        place(d)
    for d in sorted((d for d in ds if d.prio == 0), key=lambda d: d.t):
        place(d, gap_before=ROUTINE_GAP_S)
    return _quiet_fill(m, _ball_fill(m, placed, duration_of), duration_of)


def _ceil2(t: float) -> float:
    return math.ceil(t * 100 - 1e-9) / 100


def _hushes(m: Match, placed: list[Line]) -> list[tuple[float, float]]:
    return [(p.t_in, m.reveal_t(m.by_id(p.draft.evidence[0]))) for p in placed if p.draft.kind == "build"]


def _free(m: Match, placed: list[Line], a: float, b: float, kind: str, gap_before: float = MIN_GAP_S,
          gap_after: float = MIN_GAP_S) -> bool:
    if a < m.t_start - EPS or b > m.t_end + EPS:
        return False
    if kind in HUSHED and any(a < h1 and b > h0 for h0, h1 in _hushes(m, placed)):
        return False
    return all(b + gap_after <= p.t_in + EPS or a + EPS >= p.end + gap_before for p in placed)


def in_play(m: Match) -> list[tuple[float, float]]:
    """(from, to) for every stretch of the window with the ball alive, from B's 25 Hz ticks."""
    rows, hz, t0 = m.ticks["ball"]["rows"], m.ticks["ball"]["hz"], m.ticks["t0"]
    runs: list[tuple[float, float]] = []
    start = None
    for k, row in enumerate(rows):
        if row[3] and start is None:
            start = t0 + k / hz
        elif not row[3] and start is not None:
            runs.append((start, t0 + k / hz))
            start = None
    if start is not None:
        runs.append((start, t0 + len(rows) / hz))
    return [(max(a, m.t_start), min(b, m.t_end)) for a, b in runs if b > m.t_start and a < m.t_end]


def quiet_in_play(m: Match, starts: list[float], runs: list[tuple[float, float]] | None = None
                  ) -> list[tuple[float, float]]:
    """(from, to) for every stretch with the ball in play and no line starting, window start to window end."""
    runs = in_play(m) if runs is None else runs
    edges = [m.t_start, *sorted(starts), m.t_end]
    return [(max(a, r0), min(b, r1)) for a, b in zip(edges, edges[1:]) for r0, r1 in runs if min(b, r1) > max(a, r0)]


def _ball_fill(m: Match, placed: list[Line], duration_of: DurationFn) -> list[Line]:
    """Split every in-play stretch longer than BALL_EVERY_S with ball lines, evenly, left to right."""
    runs = in_play(m)
    every = getattr(lines_for(m), "BALL_EVERY_S", BALL_EVERY_S)  # lively_v2 narrates every ~3 s
    lines = sorted(placed, key=lambda p: p.t_in)
    said: dict[str, int] = {}  # holder event -> ball lines about it so far (varies the wording)
    cursor = m.t_start
    while True:
        todo = next(((s0, s1) for s0, s1 in quiet_in_play(m, [p.t_in for p in lines], runs)
                     if s0 >= cursor - EPS and s1 - s0 > every), None)
        if todo is None:
            return lines
        fit = _fit_ball(m, lines, *todo, runs, said, duration_of)
        if fit is None:
            cursor = todo[1]  # nothing fits anywhere in this stretch (a hush, or no known holder): move on
            continue
        ev = m.holder_at(fit.t_in)[1] or ""
        said[ev] = said.get(ev, 0) + 1
        lines.append(fit)
        lines.sort(key=lambda p: p.t_in)
        cursor = fit.t_in


def _fit_ball(m: Match, lines: list[Line], s0: float, s1: float, runs: list[tuple[float, float]],
              said: dict[str, int], duration_of: DurationFn) -> Line | None:
    # Even spacing: cut the stretch into the fewest equal parts no longer than BALL_EVERY_S, and aim for the first cut.
    # Try that point, then earlier, then later. The next round of _ball_fill splits whatever is left.
    every = getattr(lines_for(m), "BALL_EVERY_S", BALL_EVERY_S)
    pref = _ceil2(s0 + (s1 - s0) / math.ceil((s1 - s0) / every))
    n_back, n_fwd = int((pref - s0) / STEP_S), int((s1 - pref) / STEP_S)
    cands = [round(pref - STEP_S * k, 2) for k in range(n_back + 1)] + [round(pref + STEP_S * k, 2)
                                                                        for k in range(1, n_fwd + 1)]
    for gap in dict.fromkeys((getattr(lines_for(m), "BALL_GAP_S", BALL_GAP_S), DUCK_S)):  # room for the crowd to swell back first; at the least, room for the duck
        for a in cands:
            _, ev = m.holder_at(a)
            i = next((j for j, p in enumerate(lines) if p.t_in > a), len(lines))
            near = tuple(p.text for p in lines[max(i - 1, 0):i + 1])
            score = T.score_words(m, a)
            due = not any(score in p.text for p in lines if a - SCORE_EVERY_S <= p.t_in < a)
            d = lines_for(m).ball(m, a, said.get(ev or "", 0), near, due)
            if d is None:
                continue
            for text in d.texts:
                dur = duration_of(text, d.style, d.pause_ms)
                if (any(r0 - EPS <= a and a + dur <= r1 + EPS for r0, r1 in runs)
                        and _free(m, lines, a, a + dur, d.kind, gap_before=gap, gap_after=gap)):
                    return Line(d, text, a, dur)
    return None


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
                d = lines_for(m).state(m, a, n)
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
