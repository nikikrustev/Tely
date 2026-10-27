"""The judge-cut match as the Q&A tools see it. OWNER: B (Nikolay).

`bundle` in the qa API (TEAM_SPLIT.md seam 2) is a Bundle from load_bundle(). Every accessor takes the playhead and
returns only what the listener already knows (file 43 §2 spoiler firewall, file 40 "clamped to the delayed clock"):
- an event counts only once its outcome is revealed (signals reveal_t <= playhead);
- ball and player positions are read at the playhead, never after;
- the score is the score the listener knows at that second.
"""
from __future__ import annotations

import gzip
import json
import math
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
JUDGE = ROOT / "web" / "public" / "replay" / "v1" / "judge"
HALF_L = 52.5


@dataclass
class Bundle:
    meta: dict
    events: list[dict]          # CDF `event` objects, in time order
    signals: dict
    ticks: dict
    src: Path
    players: dict[str, dict] = field(init=False)
    side_of_team: dict[str, str] = field(init=False)

    def __post_init__(self) -> None:
        self.players, self.side_of_team = {}, {}
        for side in ("home", "away"):
            t = self.meta["teams"][side]
            self.side_of_team[t["id"]] = side
            for p in t["players"]:
                self.players[p["id"]] = {**p, "side": side}

    # ---- the window and the clock -----------------------------------------------------------------------
    @property
    def t0(self) -> float:
        return float(self.meta["judge_cut"]["t_start"])

    @property
    def t1(self) -> float:
        return float(self.meta["judge_cut"]["t_end"])

    def clamp(self, p: float) -> float:
        return min(max(float(p), self.t0), self.t1)

    @cached_property
    def clock_offset_s(self) -> int:
        mm, ss = self.meta["periods"][0]["clock_start"].split(":")
        return int(mm) * 60 + int(float(ss))

    def clock_s(self, p: float) -> float:
        return self.clock_offset_s + p

    def clock_str(self, p: float) -> str:
        c = int(self.clock_s(self.clamp(p)))
        return f"{c // 60:02d}:{c % 60:02d}"

    def parse_clock(self, mmss: str) -> float | None:
        """'56:30' (match clock) -> period seconds, or None if it can't be read."""
        try:
            mm, ss = str(mmss).strip().split(":")
            return int(mm) * 60 + float(ss) - self.clock_offset_s
        except (ValueError, AttributeError):
            return None

    def team_name(self, side: str) -> str:
        return self.meta["teams"][side]["short_name"]

    def attacks(self, side: str) -> int:
        return 1 if self.meta["teams"][side]["attacks"] == "+x" else -1

    # ---- what is known at playhead p (never later) ---------------------------------------------------------
    def sig(self, eid: str) -> dict:
        return self.signals["events"][eid]

    def known(self, p: float) -> list[dict]:
        """Events whose outcome the listener has heard by p, in time order."""
        return [e for e in self.events if self.sig(e["id"])["reveal_t"] <= p]

    def second(self, p: float) -> dict:
        rows = self.signals["per_second"]
        i = min(max(int(math.floor(self.clamp(p) - rows[0]["t"])), 0), len(rows) - 1)
        return rows[i]

    def score(self, p: float) -> dict:
        return self.second(p)["score"]

    def ball(self, p: float) -> dict:
        b = self.ticks["ball"]
        k = min(max(int(math.floor((self.clamp(p) - self.ticks["t0"]) * b["hz"])), 0), len(b["rows"]) - 1)
        x, y, z, alive, poss = b["rows"][k]
        return {"x": x, "y": y, "z": z, "alive": bool(alive), "poss": poss}

    def player_rows(self, p: float) -> tuple[list[str], list[list[float]]]:
        """Player position rows from the window start up to p (5 Hz), inclusive."""
        pl = self.ticks["players"]
        k = min(max(int(math.floor((self.clamp(p) - self.ticks["t0"]) * pl["hz"])), 0), len(pl["rows"]) - 1)
        return pl["ids"], pl["rows"][: k + 1]


def load_bundle(d: Path = JUDGE) -> Bundle:
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    events = [json.loads(s)["event"] for s in (d / "events.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
    signals = json.loads((d / "signals.json").read_text(encoding="utf-8"))
    ticks = json.loads(gzip.decompress((d / "ticks.json.gz").read_bytes()))
    return Bundle(meta=meta, events=events, signals=signals, ticks=ticks, src=d)
