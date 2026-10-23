"""The Director agent: reads the look-ahead window [P, P + D] and outputs only a tension plan. OWNER: A (potencialbg).

File 43 §2 firewall: the Director may output build_up_level, lead_s, hold_ms and hint_type ("danger, not result"),
and never the outcome of a future event. Three layers keep that true:
1. features() is the firewall. It copies an allow-list of fields out of the window (event types, zones, xG, seconds
   to the shot) and nothing else: no outcome_type, no shot end point, no VAR, no related save/block, no signals text.
   A goal and a save with the same build-up give byte-identical features (tests/a/test_director.py).
2. The model's reply must match SCHEMA exactly; validate() (the Verifier, in code) rejects anything else, including a
   hint the window does not support ("on the break!" with no regain is a false statement).
3. Any failure (no quota, 429, timeout, bad JSON, schema) falls back to the rules Director for that window, and the
   fallback is recorded.

The model client is Agent Framework's FoundryChatClient (file 18 §3, agent-framework 1.23), imported lazily: CI never
installs requirements-azure.txt, so this module, the schema and the firewall must import without it.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from audiostands.commentary.source import Match
from audiostands.commentary.templates import LEAD_S
from audiostands.spoiler import D_S

VERSION = "dir_v1"
LEAD_RANGE = (3.5, 4.5)   # LEAD_S ± 0.5 (Stage 3 check); 10 - 4.5 still leaves 5.5 s of the 6 s wall budget (file 43 §2)
HOLD_RANGE = (0, 800)     # silence after the build-up, ms (our choice: longer and the reveal can arrive mid-hold)
HINTS = ("danger", "counter", "set_piece", "none")
SET_PIECES = {"free_kick", "corner_kick", "corner", "penalty"}
REGAINS = {"interception", "tackle", "recovery", "clearance"}  # SEAM(A->B): defending sub_types, contract 0.2.0
MAX_EVENTS = 12           # keeps one call well under file 43's 1,200 tokens (prompt + output)
TIMEOUT_S = 8.0           # deadline for one model call; on expiry the window falls back to rules

SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["build_up_level", "lead_s", "hold_ms", "hint_type"],
    "properties": {
        "build_up_level": {"type": "number", "minimum": 0, "maximum": 1},
        "lead_s": {"type": "number", "minimum": LEAD_RANGE[0], "maximum": LEAD_RANGE[1]},
        "hold_ms": {"type": "integer", "minimum": HOLD_RANGE[0], "maximum": HOLD_RANGE[1]},
        "hint_type": {"type": "string", "enum": list(HINTS)},
    },
}

INSTRUCTIONS = f"""You are the Director of a radio football commentary for blind and low-vision fans.
You see the next {D_S:.0f} seconds of play before the listener hears them, but never the result of any shot.
For the shot at the end of the window, decide how the commentator builds tension before it.
Reply with one JSON object and nothing else:
- build_up_level: 0 to 1. Below 0.3 means no build-up line (a hopeful effort); 0.5 a real chance; 0.8+ a big chance.
  Judge it from xg, where the shot comes from, and how the move built up. Never from what you think will happen.
- lead_s: {LEAD_RANGE[0]} to {LEAD_RANGE[1]}, seconds before the shot that the build-up starts. Earlier for a move
  that builds slowly, later for a sudden chance.
- hold_ms: {HOLD_RANGE[0]} to {HOLD_RANGE[1]}, a beat of silence after the build-up line.
- hint_type: "counter" only if the attacking team won the ball back in this window; "set_piece" only if the attack
  comes from a free kick, corner or penalty in this window; "danger" for a clear chance; otherwise "none".
Never predict, imply or hint whether the shot scores, is saved, blocked or missed."""


@dataclass(frozen=True)
class Plan:
    build_up_level: float
    lead_s: float
    hold_ms: int
    hint_type: str

    def to_dict(self) -> dict:
        return asdict(self)


class PlanError(ValueError):
    """The Verifier rejected a Director reply. The window falls back to rules."""


# --- 1. the firewall ---------------------------------------------------------------------------------------------

def features(m: Match, shot: dict) -> dict:
    """Compact window [P, P + D] for one shot, with P = shot time - D. Allow-list only: see the module docstring."""
    t_shot = m.t(shot)
    p = t_shot - D_S
    side = m.side(shot)
    sig = m.sig(shot["id"])
    window = [e for e in m.events if p <= m.t(e) < t_shot and e["type"] != "referee"][-MAX_EVENTS:]
    score = m.score_at(max(p, m.t_start))
    return {
        "minute": int(m.clock_s(max(p, m.t_start)) // 60),
        "score": {"attacking": score[side], "defending": score["away" if side == "home" else "home"]},
        "tension_now": round(m.second(max(p, m.t_start))["tension"], 2),
        # SEAM(A->B): B's tension is an xG-weighted look-ahead, the same for a goal and a save (signals.json).
        "tension_before_shot": round(m.second(max(t_shot - LEAD_S, m.t_start))["tension"], 2),
        "events": [{"in_s": round(m.t(e) - p, 1), "type": e["type"], "sub_type": e.get("sub_type"),
                    "team": "attacking" if m.side(e) == side else "defending",
                    "zone": m.sig(e["id"])["zone"]["words"]} for e in window],
        "shot": {"in_s": round(t_shot - p, 1), "xg": round(sig["xg"] or 0.0, 3), "zone": sig["zone"]["words"],
                 "in_box": bool(sig["zone"].get("in_box")), "body_part": shot.get("body_part")},
    }


def regained(feat: dict) -> bool:
    return any(e["team"] == "attacking" and e["type"] == "defending" and e["sub_type"] in REGAINS
               for e in feat["events"])


def set_piece(feat: dict) -> bool:
    return any(e["team"] == "attacking" and e["sub_type"] in SET_PIECES for e in feat["events"])


# --- 2. the Verifier (code) --------------------------------------------------------------------------------------

def _number(obj: dict, key: str, lo: float, hi: float, integer: bool = False) -> float:
    v = obj[key]
    if isinstance(v, bool) or not isinstance(v, int if integer else (int, float)):
        raise PlanError(f"{key}={v!r} is not {'an integer' if integer else 'a number'}")
    if not lo <= v <= hi:
        raise PlanError(f"{key}={v!r} outside [{lo}, {hi}]")
    return v


def validate(obj: Any, feat: dict) -> Plan:
    """SCHEMA, checked by hand (jsonschema is not a CI dependency), plus: a hint must be true of the window."""
    if not isinstance(obj, dict):
        raise PlanError(f"reply is {type(obj).__name__}, not an object")
    keys = set(obj)
    want = set(SCHEMA["required"])
    if keys != want:
        raise PlanError(f"fields {sorted(keys)} != {sorted(want)}")
    level = _number(obj, "build_up_level", 0, 1)
    lead = _number(obj, "lead_s", *LEAD_RANGE)
    hold = _number(obj, "hold_ms", *HOLD_RANGE, integer=True)
    hint = obj["hint_type"]
    if hint not in HINTS:
        raise PlanError(f"hint_type={hint!r} not in {HINTS}")
    if hint == "counter" and not regained(feat):
        raise PlanError("hint_type=counter but the attacking team won nothing back in this window")
    if hint == "set_piece" and not set_piece(feat):
        raise PlanError("hint_type=set_piece but there is no set piece in this window")
    return Plan(round(float(level), 2), round(float(lead), 1), int(hold), hint)


def parse(raw: str, feat: dict) -> Plan:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PlanError(f"not JSON: {exc.msg}") from None
    return validate(obj, feat)


# --- 3. the model ------------------------------------------------------------------------------------------------

@dataclass
class Reply:
    raw: str
    latency_ms: float
    tokens: dict


class DirectorModel(Protocol):
    name: str

    async def ask(self, key: str, feat: dict) -> Reply:
        """One model call for one window. Raises on any transport, quota or timeout error."""


_JWT = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+")


def scrub(text: str) -> str:
    """Error text goes into fixtures and the eval report: drop anything shaped like a bearer token."""
    return _JWT.sub("***", text)


def prompt(feat: dict) -> str:
    return json.dumps(feat, separators=(",", ":"))


class FoundryDirector:
    """Agent Framework Agent on a Foundry model deployment (FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_MODEL; keyless)."""

    def __init__(self, env: dict[str, str]):
        from agent_framework import Agent
        from agent_framework.foundry import FoundryChatClient
        from azure.identity import DefaultAzureCredential

        self.model = env["FOUNDRY_MODEL"]
        self.name = f"{VERSION}@{self.model}"
        # WHY: file 18 §3, FoundryChatClient on the project endpoint; keyless (az login / managed identity).
        self.client = FoundryChatClient(project_endpoint=env["FOUNDRY_PROJECT_ENDPOINT"], model=self.model,
                                        credential=DefaultAzureCredential(exclude_interactive_browser_credential=True))
        self.agent = Agent(client=self.client, name="Director", id="director-agent", instructions=INSTRUCTIONS,
                           description="Plans commentary tension from the look-ahead window; never sees outcomes")
        self.options = {
            "response_format": {"type": "json_schema", "json_schema": {"name": "tension_plan", "schema": SCHEMA,
                                                                       "strict": True}},
            "reasoning": {"effort": "minimal"},  # gpt-5-mini is a reasoning model; the plan needs no long thought
            "max_tokens": 200,
        }

    async def ask(self, key: str, feat: dict) -> Reply:
        t0 = time.perf_counter()
        res = await asyncio.wait_for(self.agent.run(prompt(feat), options=self.options), timeout=TIMEOUT_S)
        usage = res.usage_details or {}
        tokens = {"input": usage.get("input_token_count"), "output": usage.get("output_token_count")}
        return Reply(res.text, (time.perf_counter() - t0) * 1000, tokens)


class ReplayDirector:
    """Recorded Director replies (tests/a/fixtures), so CI runs DIRECTOR=foundry with no Azure call.

    A fixture entry {"error": "..."} replays a failure, for example a 429, as an exception.
    """

    def __init__(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.name = data["director"]  # same name as the live run, so a replayed build is byte-identical
        self.replies = {r["key"]: r for r in data["calls"]}

    async def ask(self, key: str, feat: dict) -> Reply:
        r = self.replies.get(key)
        if r is None:
            raise LookupError(f"no recorded reply for {key}")
        if r.get("error"):
            raise RuntimeError(r["error"])
        if r.get("features") is not None and r["features"] != feat:
            raise LookupError(f"recorded features for {key} differ from today's window (re-record the fixture)")
        return Reply(r["raw"], r.get("latency_ms", 0.0), r.get("tokens", {}))


class RecordingDirector:
    """Wraps a live Director and keeps every call, to write a fixture. Stores no keys, tokens or audio."""

    def __init__(self, inner: DirectorModel):
        self.inner, self.name, self.calls = inner, inner.name, []

    async def ask(self, key: str, feat: dict) -> Reply:
        try:
            r = await self.inner.ask(key, feat)
        except Exception as exc:
            self.calls.append({"key": key, "features": feat, "error": scrub(f"{type(exc).__name__}: {exc}")[:300]})
            raise
        self.calls.append({"key": key, "features": feat, "raw": r.raw, "latency_ms": round(r.latency_ms, 1),
                           "tokens": r.tokens})
        return r

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        body = {"director": self.name, "recorded": time.strftime("%Y-%m-%d"), "calls": self.calls}
        path.write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
