"""Numeric truth: every number a line speaks, graded against the synthetic ground truth (file 18 §5). OWNER: A.

One dataset item per spoken line that states a number: the claims parsed from its text, and the truth at its t_in
(score, minutes played). The ground truth sits inside the item because Foundry's code-based evaluator sandbox has no
network (file 18 §5). grade() is the grader: it runs locally in CI, and --foundry-eval uploads its exact source as a
Foundry code-based custom evaluator (preview) and runs it once over the same items.
"""

from __future__ import annotations

import inspect
import json
import re
import time

from tely.commentary.source import Match
from tely.commentary.verifier import _NUM_RE, _WORD_NUM

EVALUATOR = "tely-numeric-truth"


def grade(sample: dict, item: dict) -> float:
    """Share of the item's claims that match its truth (file 18 §5). An item with no claims scores 1.0."""
    claims, truth = item.get("claims", []), item.get("truth", {})
    if not claims:
        return 1.0
    ok = sum(1 for c in claims if abs(truth.get(f'{c["metric"]}:{c["subject"]}', 1e9) - c["value"]) <= 0.05)
    return ok / len(claims)


def claims(m: Match, text: str) -> list[dict]:
    """Numbers a line states: "<team> <number>" scores and "<number> minutes played" (the only numbers we speak)."""
    low, out = text.lower(), []
    for side in ("home", "away"):
        for hit in re.finditer(rf"\b{re.escape(m.team_name(side).lower())} ({_NUM_RE})\b", low):
            out.append({"metric": "score", "subject": side, "value": _WORD_NUM[hit.group(1)]})
    for hit in re.finditer(rf"\b({_NUM_RE}) minutes? played\b", low):
        out.append({"metric": "minute", "subject": "clock", "value": _WORD_NUM[hit.group(1)]})
    if "inside the first minute" in low:
        out.append({"metric": "minute", "subject": "clock", "value": 0})
    return out


def dataset(m: Match, cues: list[dict]) -> list[dict]:
    items = []
    for c in cues:
        cl = claims(m, c["text"]["radio"])
        if not cl:
            continue
        score = m.score_at(c["t_in"])
        items.append({"cue_id": c["cue_id"], "text": c["text"]["radio"], "claims": cl,
                      "truth": {"score:home": score["home"], "score:away": score["away"],
                                "minute:clock": int(m.clock_s(c["t_in"]) // 60)}})
    return items


def run_local(items: list[dict]) -> dict:
    scores = [grade({}, it) for it in items]
    n_claims = sum(len(it["claims"]) for it in items)
    ok = sum(round(s * len(it["claims"])) for s, it in zip(scores, items))
    return {"where": "local", "items": len(items), "claims": n_claims, "claims_verified": ok,
            "pct_verified": round(100 * ok / n_claims, 1) if n_claims else None,
            "failed": [it["cue_id"] for s, it in zip(scores, items) if s < 1.0]}


# --- Foundry (preview): upload grade() as a code-based custom evaluator and run it once ------------------------------

DATA_SCHEMA = {
    "type": "object",
    "properties": {"claims": {"type": "array"}, "truth": {"type": "object"}},
    "required": ["claims", "truth"],
}


def run_foundry(items: list[dict], env: dict[str, str], timeout_s: float = 600) -> dict:
    """Returns the Foundry run's result, or {"where": "local-only", "reason": ...} if the SDK or service refuses."""
    try:
        from azure.ai.projects import AIProjectClient
        from azure.ai.projects.models import CodeBasedEvaluatorDefinition, EvaluatorMetric
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        return {"where": "local-only", "reason": f"azure-ai-projects not installed ({exc.name})"}
    step = "connect"
    try:
        project = AIProjectClient(endpoint=env["FOUNDRY_PROJECT_ENDPOINT"],
                                  credential=DefaultAzureCredential(exclude_interactive_browser_credential=True))
        step = "create evaluator"
        ev = project.beta.evaluators.create_version(name=EVALUATOR, evaluator_version={
            "display_name": "Tely numeric truth",
            "description": "Share of a commentary line's spoken numbers (score, minutes) that match the synthetic truth.",
            "evaluator_type": "custom", "categories": ["quality"],
            "definition": CodeBasedEvaluatorDefinition(
                code_text=inspect.getsource(grade), data_schema=DATA_SCHEMA,
                metrics={"numeric_truth": EvaluatorMetric(type="continuous", desirable_direction="increase",
                                                          min_value=0, max_value=1, threshold=1.0)}),
        })
        step = "create eval"
        oai = project.get_openai_client()
        evaluation = oai.evals.create(
            name="tely-numeric-truth",
            data_source_config={"type": "custom", "item_schema": DATA_SCHEMA, "include_sample_schema": False},
            testing_criteria=[{"type": "azure_ai_evaluator", "name": "numeric_truth", "evaluator_name": EVALUATOR,
                               "evaluator_version": ev.version,
                               "data_mapping": {"claims": "{{item.claims}}", "truth": "{{item.truth}}"}}])
        step = "create run"
        run = oai.evals.runs.create(eval_id=evaluation.id, name="judge-cut", data_source={
            "type": "jsonl", "source": {"type": "file_content",
                                        "content": [{"item": {"claims": it["claims"], "truth": it["truth"]}}
                                                    for it in items]}})
        step = "wait for run"
        t0 = time.time()
        while run.status in ("queued", "in_progress") and time.time() - t0 < timeout_s:
            time.sleep(5)
            run = oai.evals.runs.retrieve(run.id, eval_id=evaluation.id)
        counts = getattr(run, "result_counts", None)
        return {"where": "foundry", "evaluator": f"{EVALUATOR}:{ev.version}", "eval_id": evaluation.id,
                "run_id": run.id, "status": run.status, "report_url": getattr(run, "report_url", None),
                "result_counts": counts.model_dump() if hasattr(counts, "model_dump") else counts,
                "error": str(getattr(run, "error", None) or "") or None}
    except Exception as exc:  # preview API: any refusal means we keep the local grade and say so
        from tely.agents.director import scrub

        return {"where": "local-only", "reason": scrub(f"{step}: {type(exc).__name__}: {exc}")[:400]}


def items_json(items: list[dict]) -> str:
    return "\n".join(json.dumps(it, ensure_ascii=False) for it in items)
