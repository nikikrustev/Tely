"""(a) The offline numbers for one built cut: spoiler firewall, numbers, fallbacks, Director.

Everything here reads the committed bundle and the recorded Director replies, so it needs no Azure and runs in CI.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from tely import spoiler
from tely.agents import director as dir_agent
from tely.agents import rules_director
from tely.agents import workflow as W
from tely.commentary import planner
from tely.commentary.source import BUNDLE, Match
from tely.commentary.ssml import build_ssml, ssml_sha256
from tely.eval import numeric_truth


def load_cues(cut: str, bundle: Path = BUNDLE) -> list[dict]:
    path = bundle / cut / "cues.en.radio.jsonl"
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


def firewall(m: Match, cues: list[dict]) -> dict:
    events = spoiler.flat_events(m)
    leaks = spoiler.spoiler_leaks(cues, events)
    return {"spoiler_leaks": len(leaks), "spoiler_leak_list": leaks, "spoiler_lift": spoiler.spoiler_lift(cues, events),
            "spoiler_check_pass": sum(c["spoiler_check"] == "pass" for c in cues)}


def text_fallbacks(m: Match, cues: list[dict], plans: dict, voice: str, durations: dict[str, int]) -> dict:
    """Which lines are spoken with a shorter fallback text than their template's first choice.

    Re-plans with the cached real durations (the same inputs the build used) to recover each line's Draft.
    """
    def dur(text: str, style: str, pause: int) -> float:
        ms = durations.get(ssml_sha256(build_ssml(text, style, voice, pause_after_ms=pause)))
        return ms / 1000 if ms is not None else planner.estimate(text, style, pause)

    lines = planner.plan(m, dur, plans)
    same = [ln.text for ln in lines] == [c["text"]["radio"] for c in cues]
    short = [ln for ln in lines if ln.text != ln.draft.texts[0]]
    by_kind = Counter(ln.draft.kind for ln in short)
    return {"replan_matches_bundle": same, "lines": len(lines), "shorter_text": len(short),
            "shorter_text_pct": round(100 * len(short) / len(lines), 1) if lines else None,
            "shorter_text_by_kind": dict(sorted(by_kind.items()))}


def director(m: Match, recorded: Path | None, cues: list[dict]) -> tuple[dict, dict]:
    """Director calls and fallbacks: replays the recorded Foundry replies through the same workflow, plus the
    rules plan for each window side by side (the A/B the README and video talk about)."""
    model = dir_agent.ReplayDirector(recorded) if recorded and recorded.is_file() else None
    run = W.direct(m, model, None, "replay" if model else "rules")
    rec = json.loads(recorded.read_text(encoding="utf-8")) if model else {"calls": []}
    lat = sorted(c["latency_ms"] for c in rec["calls"] if "latency_ms" in c)
    spoken = {c["evidence"][0]: c["text"]["radio"] for c in cues if c["kind"] == "build"}
    s = run.summary()
    reasons = Counter((r["fallback"] or "").split(":")[0] for r in s["log"] if r["fallback"])
    return {
        "name": run.name, "recorded": rec.get("recorded"), "engine": run.engine, "windows": s["windows"],
        "calls": s["director_calls"], "model_plans": s["model_plans"], "fallbacks": s["fallbacks"],
        "fallbacks_after_a_call": s["fallbacks_after_a_call"], "fallback_reasons": dict(reasons),
        "rules_by_budget": s["rules_by_budget"],
        "tokens_per_call": round((s["tokens_in"] + s["tokens_out"]) / s["director_calls"]) if s["director_calls"] else None,
        "model_latency_ms_recorded": lat,
        "windows_detail": [{"key": r["key"], "t_shot": r["t_shot"], "director": r["director"], "plan": r["plan"],
                            "rules_plan": rules_director.plan(st.window.feat).to_dict(),
                            "spoken_build_line": spoken.get(r["key"]), "fallback": r["fallback"]}
                           for r, st in zip(s["log"], run.steps)],
    }, run.plans


def report(m: Match, cut: str, voice: str, recorded: Path | None, bundle: Path = BUNDLE) -> dict:
    cues = load_cues(cut, bundle)
    idx = json.loads((bundle / cut / "audio" / "en" / "radio" / "index.json").read_text(encoding="utf-8"))
    durations = {sha: v["duration_ms"] for sha, v in idx.items()}
    dir_rep, plans = director(m, recorded, cues)
    items = numeric_truth.dataset(m, cues)
    return {
        "cut": cut, "lines": len(cues),
        **firewall(m, cues),
        "truth_check_pass": sum(c["truth_check"] == "pass" for c in cues),
        "numbers": numeric_truth.run_local(items),
        "templates": {"template_lines": len(cues), "llm_lines": 0,
                      "note": "Every spoken line is a template; the LLM stays off the hot path (file 43 §2). "
                              "The optional LLM colour lines were skipped (docs/DECISIONS.md D16).",
                      **text_fallbacks(m, cues, plans, voice, durations)},
        "director": dir_rep,
    }
