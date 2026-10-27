"""The one delayed clock and the spoiler firewall (file 43 §2-§3). OWNER: B (Nikolay).

Truth time t runs D_S seconds ahead of what the listener hears (playhead P = t - D_S). Only the Director and the
Commentator see the window [P, P + D_S]. Q&A tools, catch-up and crowd outcome reactions see only <= P.
"""
from __future__ import annotations

D_S, PREFETCH_S = 10.0, 3.0      # file 43 / file 39: look-ahead (broadcast delay) and audio prefetch


class Clock:
    def __init__(self, t0_wall: float):
        self.t0 = t0_wall                            # wall time of truth t = 0

    def truth(self, now: float) -> float:
        return now - self.t0

    def playhead(self, now: float) -> float:
        return self.truth(now) - D_S


def director_window(events: list, clk: Clock, now: float) -> list:
    """Director / Commentator only: events in [P, P + D]. They may use time and xG, never outcomes."""
    p = clk.playhead(now)
    return [e for e in events if p <= e["t"] <= p + D_S]


def qa_view(events: list, clk: Clock, now: float) -> list:
    """Q&A tools, catch-up, crowd reactions: only events the listener has already heard (t <= P)."""
    p = clk.playhead(now)
    return [e for e in events if e["t"] <= p]


# SEAM(B->A): release() is the gate A's relay/server uses before a cue leaves the server (file 43 §3 cue contract)
def release(cues: list, clk: Clock, now: float, sent: set) -> list:
    """Cues that may leave the server now: t_in <= P + PREFETCH_S, each once, with the SSML stripped."""
    p = clk.playhead(now)
    out = []
    for c in cues:
        if c["t_in"] <= p + PREFETCH_S and c["cue_id"] not in sent:
            c = {**c, "utterance": {k: v for k, v in c.get("utterance", {}).items() if k != "ssml"}}
            out.append(c)
            sent.add(c["cue_id"])
    return out
