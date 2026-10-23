"""Director -> Commentator (templates) -> Verifier (code) -> TTS, once per Director window. OWNER: A (potencialbg).

File 43 §1: the Director decides, templates write, code verifies, Azure Speech renders. One window per shot: the
Director first learns of a shot when truth time reaches it, with the listener's playhead D = 10 s behind, so the
build-up line (shot - lead_s) has 10 - lead_s seconds of wall time for plan -> verify -> TTS (file 43 §2).

Budget (file 43 §4): at most one Director call per CALL_EVERY_S of match time. A shot that comes sooner after the
last call is planned by rules, and the log says so. So is every window where the model fails or the Verifier rejects
its reply: the commentary never waits on the model.

The four steps are plain functions, so CI (no agent-framework) runs them in order with the same results. With
agent-framework installed, af_workflow.py wraps them as Agent Framework executors on a WorkflowBuilder graph, which
gives the OpenTelemetry spans that tracing.py sends to Application Insights (file 18 §5).
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import time
from dataclasses import dataclass, field
from typing import Callable

from audiostands.agents import rules_director
from audiostands.agents.director import LEAD_RANGE, DirectorModel, Plan, PlanError, features, parse, scrub
from audiostands.commentary import templates as T
from audiostands.commentary import verifier
from audiostands.commentary.source import Match

CALL_EVERY_S = 10.0  # file 43 §4: one Director call per 10 s of match time at most
MODES = ("foundry", "replay", "rules")

RenderFn = Callable[[T.Draft], tuple[str, int]]  # draft -> (ssml sha256, duration ms); renders if not cached


@dataclass
class Window:
    key: str                 # the shot's event id
    shot: dict
    t_shot: float
    feat: dict
    call: bool               # False: rules only (budget, or the build-up would start before the cut)
    skip_reason: str | None = None


@dataclass
class Step:
    """What travels along the workflow edges for one window. Each step fills in its part."""

    window: Window
    plan: Plan | None = None
    director: str = rules_director.NAME
    fallback: str | None = None          # why rules planned this window instead of the model
    raw: str | None = None               # the model's reply, verbatim (no keys or tokens in it)
    tokens: dict = field(default_factory=dict)
    plan_ms: float = 0.0
    draft: T.Draft | None = None
    errors: list[str] = field(default_factory=list)
    verify_ms: float = 0.0
    sha: str | None = None
    tts_ms: float = 0.0

    def record(self) -> dict:
        w = self.window
        return {"key": w.key, "t_shot": round(w.t_shot, 2), "director": self.director, "fallback": self.fallback,
                "plan": self.plan.to_dict() if self.plan else None, "raw": self.raw, "tokens": self.tokens,
                "build_line": self.draft.texts[0] if self.draft else None,
                "t_build": round(self.draft.t, 2) if self.draft else None,
                "plan_ms": round(self.plan_ms, 1), "verify_ms": round(self.verify_ms, 1),
                "tts_ms": round(self.tts_ms, 1), "errors": self.errors}


def windows(m: Match) -> list[Window]:
    out, last_call = [], None
    for e in m.events:
        t = m.t(e)
        if e["type"] != "shot" or not m.t_start <= t < m.t_end:
            continue
        w = Window(e["id"], e, t, features(m, e), call=True)
        if t - LEAD_RANGE[0] < m.t_start:
            w.call, w.skip_reason = False, "no room: a build-up would start before the cut"
        elif last_call is not None and t - last_call < CALL_EVERY_S:
            w.call, w.skip_reason = False, f"budget: last Director call {t - last_call:.1f} s earlier (max 1 per 10 s)"
        else:
            last_call = t
        out.append(w)
    return out


# --- the four steps ------------------------------------------------------------------------------------------------

async def director_step(w: Window, model: DirectorModel | None) -> Step:
    s = Step(w)
    t0 = time.perf_counter()
    if model is not None and w.call:
        try:
            reply = await model.ask(w.key, w.feat)
            s.raw, s.tokens = reply.raw, reply.tokens
            s.plan, s.director = parse(reply.raw, w.feat), model.name
        except PlanError as exc:
            s.fallback = f"verifier: {exc}"
        except Exception as exc:  # 429, quota, timeout, network: this window falls back to rules
            s.fallback = scrub(f"model: {type(exc).__name__}: {exc}")[:300]
    elif model is not None:
        s.fallback = w.skip_reason
    if s.plan is None:
        s.plan, s.director = rules_director.plan(w.feat), rules_director.NAME
    s.plan_ms = (time.perf_counter() - t0) * 1000
    return s


def commentator_step(m: Match, s: Step) -> Step:
    s.draft = T.build(m, s.window.shot, s.plan)
    return s


def verifier_step(m: Match, s: Step) -> Step:
    """truth_check + spoiler_check on every text the build-up may speak. A failing Director plan falls back to rules."""
    t0 = time.perf_counter()

    def check(d: T.Draft | None) -> list[str]:
        if d is None:
            return []
        return [err for text in d.texts for err in (verifier.truth_check(m, text, d.t, list(d.evidence)) +
                                                    verifier.spoiler_check(m, text, d.t, list(d.evidence)))]

    s.errors = check(s.draft)
    if s.errors and s.director != rules_director.NAME:
        s.fallback = f"verifier: {s.errors[0]}"
        s.plan, s.director = rules_director.plan(s.window.feat), rules_director.NAME
        s.draft = T.build(m, s.window.shot, s.plan)
        s.errors = check(s.draft)
    s.verify_ms = (time.perf_counter() - t0) * 1000
    return s


def tts_step(s: Step, render: RenderFn | None) -> Step:
    """Pre-render the build-up's preferred text, so it is ready before its t_in (file 43 §2)."""
    t0 = time.perf_counter()
    if s.draft is not None and render is not None:
        s.sha, _ = render(s.draft)
    s.tts_ms = (time.perf_counter() - t0) * 1000
    return s


async def run_window(m: Match, w: Window, model: DirectorModel | None, render: RenderFn | None) -> Step:
    """The same four steps, in order, without Agent Framework (CI, or agent-framework not installed)."""
    s = await director_step(w, model)
    return tts_step(verifier_step(m, commentator_step(m, s)), render)


# --- runner --------------------------------------------------------------------------------------------------------

def use_agent_framework() -> bool:
    return os.environ.get("AUDIOSTANDS_NO_AF") != "1" and importlib.util.find_spec("agent_framework") is not None


@dataclass
class DirectorRun:
    mode: str
    engine: str                      # "agent-framework" or "plain"
    steps: list[Step]

    @property
    def plans(self) -> dict[str, Plan]:
        return {s.window.key: s.plan for s in self.steps if s.plan is not None}

    @property
    def name(self) -> str:
        names = sorted({s.director for s in self.steps})
        return "+".join(names) if names else rules_director.NAME

    def summary(self) -> dict:
        model = [s for s in self.steps if s.window.call and self.mode != "rules"]
        return {"mode": self.mode, "engine": self.engine, "windows": len(self.steps),
                "director_calls": len(model), "model_plans": sum(s.director != rules_director.NAME for s in self.steps),
                "fallbacks": sum(s.fallback is not None for s in self.steps),
                "fallbacks_after_a_call": sum(s.fallback is not None for s in model),
                "rules_by_budget": sum(not s.window.call for s in self.steps),
                "tokens_in": sum(s.tokens.get("input") or 0 for s in self.steps),
                "tokens_out": sum(s.tokens.get("output") or 0 for s in self.steps),
                "log": [s.record() for s in self.steps]}


async def direct_async(m: Match, model: DirectorModel | None, render: RenderFn | None = None,
                       mode: str = "rules") -> DirectorRun:
    ws = windows(m)
    if use_agent_framework():
        from audiostands.agents import af_workflow

        steps = [await af_workflow.run_window(m, w, model, render) for w in ws]
        return DirectorRun(mode, "agent-framework", steps)
    return DirectorRun(mode, "plain", [await run_window(m, w, model, render) for w in ws])


def direct(m: Match, model: DirectorModel | None, render: RenderFn | None = None, mode: str = "rules") -> DirectorRun:
    return asyncio.run(direct_async(m, model, render, mode))
