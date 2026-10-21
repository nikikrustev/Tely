"""Load one match in B's format (contracts/b/README.md, v0.1.0) and answer "what is true at time t?".

OWNER: A (potencialbg). Everything in Stage 3 reads the match through load_match(), and nothing else parses B's files.
"""

from __future__ import annotations

import gzip
import json
import math
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / "web" / "public" / "replay" / "v1"

# SEAM(A->B): match format v0.1.0 (contracts/b/). B's Stage 1 writes the real judge cut to BUNDLE / "judge".
# Until that merges we build against B's hand-written 90 s sample. Switching is this one line:
#   "judge": BUNDLE / "judge",
MATCH_DIRS = {"judge": ROOT / "contracts" / "b" / "sample"}


@dataclass
class Match:
    """The four contract files, plus the lookups the planner and verifier need."""

    meta: dict
    events: list[dict]  # CDF `event` objects, in time order
    signals: dict
    ticks: dict
    src: Path
    players: dict[str, dict] = field(init=False)
    team_of_id: dict[str, str] = field(init=False)  # CDF team id -> "home" / "away"

    def __post_init__(self) -> None:
        self.players = {}
        self.team_of_id = {}
        for side in ("home", "away"):
            team = self.meta["teams"][side]
            self.team_of_id[team["id"]] = side
            for p in team["players"]:
                self.players[p["id"]] = {**p, "side": side}

    # --- per event -------------------------------------------------------------------------------------------
    def sig(self, event_id: str) -> dict:
        return self.signals["events"][event_id]

    def t(self, e: dict) -> float:
        return self.sig(e["id"])["t"]

    def reveal_t(self, e: dict) -> float:
        return self.sig(e["id"])["reveal_t"]

    def side(self, e: dict) -> str:
        return self.team_of_id[e["team_id"]]

    def by_id(self, event_id: str) -> dict:
        return self._by_id[event_id]

    @cached_property
    def _by_id(self) -> dict[str, dict]:
        return {e["id"]: e for e in self.events}

    # --- names -----------------------------------------------------------------------------------------------
    def team_name(self, side: str) -> str:
        return self.meta["teams"][side]["short_name"]

    def other(self, side: str) -> str:
        return "away" if side == "home" else "home"

    def surname(self, player_id: str) -> str:
        return self.players[player_id]["last_name"]

    # --- the window ------------------------------------------------------------------------------------------
    @property
    def t_start(self) -> float:
        return float(self.meta["judge_cut"]["t_start"])

    @property
    def t_end(self) -> float:
        return float(self.meta["judge_cut"]["t_end"])

    @property
    def seed(self) -> int:
        return self.meta["judge_cut"].get("seed") or 0

    def clock_s(self, t: float) -> float:
        """Match clock in seconds at t: the period's clock_start ("45:00.00" for a second half) plus t."""
        mm, ss = self.meta["periods"][0]["clock_start"].split(":")
        return int(mm) * 60 + float(ss) + t

    def match_clock(self, t: float) -> str:
        c = self.clock_s(t)
        return f"{int(c // 60):02d}:{int(c % 60):02d}"

    # --- what is true at time t (never later) ----------------------------------------------------------------
    def second(self, t: float) -> dict:
        """The per-second signal row at or before t."""
        rows = self.signals["per_second"]
        i = min(max(int(math.floor(t - rows[0]["t"])), 0), len(rows) - 1)
        return rows[i]

    def ball(self, t: float) -> dict:
        b = self.ticks["ball"]
        k = min(max(round((t - self.ticks["t0"]) * b["hz"]), 0), len(b["rows"]) - 1)
        x, y, z, alive, poss = b["rows"][k]
        return {"x": x, "y": y, "z": z, "alive": bool(alive), "poss": poss}

    def score_at(self, t: float) -> dict[str, int]:
        """Goals whose outcome is revealed by t. Computed from events, so the verifier doesn't trust signals alone."""
        score = {"home": 0, "away": 0}
        for e in self.events:
            if e["type"] == "shot" and e["outcome_type"] == "successful" and self.reveal_t(e) <= t:
                score[self.side(e)] += 1
        return score

    def holder_at(self, t: float) -> tuple[str | None, str | None]:
        """(player_id, event_id) of who has the ball at t, as far as anyone can know at t; (None, None) if in flight."""
        for e in reversed(self.events):
            et, rt = self.t(e), self.reveal_t(e)
            if et > t:
                continue
            if rt > t:
                return None, None  # pass or shot still travelling: the receiver is not known yet
            if e["type"] == "pass" and e["outcome_type"] == "successful":
                return e["receiver_id"], e["id"]
            if e["type"] in ("goalkeeping", "defending"):
                return e["player_id"], e["id"]
            return None, None  # a shot, or an intercepted pass whose interception comes next
        return None, None


def load_match(cut: str = "judge") -> Match:
    """The one place Stage 3 reads B's match files (stdlib only, as in contracts/b/README.md)."""
    d = MATCH_DIRS[cut]
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    files = meta.get("files", {})
    events_txt = (d / files.get("events", "events.jsonl")).read_text(encoding="utf-8")
    events = [json.loads(line)["event"] for line in events_txt.splitlines() if line.strip()]
    signals = json.loads((d / files.get("signals", "signals.json")).read_text(encoding="utf-8"))
    ticks = json.loads(gzip.decompress((d / files.get("ticks", "ticks.json.gz")).read_bytes()))
    return Match(meta=meta, events=events, signals=signals, ticks=ticks, src=d)
