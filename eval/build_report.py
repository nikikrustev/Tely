"""Merge the eval numbers into eval/report.md. OWNER: A (potencialbg). Stdlib only, no Azure, no keys.

    python eval/build_report.py

Reads (TEAM_SPLIT.md "The seams" point 5):
    eval/report.json      A: spoiler firewall, numbers, Director, real-time latency (python -m audiostands.eval)
    eval/qa.json          B: Q&A eval questions through answer_text(), if present
    eval/listening.json   B: the eyes-closed listening test, if present
B's two files have no fixed shape, so they are rendered generically: scalars in a table, nested objects one level
deep, lists of rows as a table. A missing file is reported as missing, never invented.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX_ROWS = 40


def load(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def cell(v) -> str:
    if v is None:
        return "–"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:g}"
    if isinstance(v, (dict, list)):
        v = json.dumps(v, ensure_ascii=False)
    return str(v).replace("|", "\\|").replace("\n", " ")


def table(header: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows]
    return out


def generic(data, title: str) -> list[str]:
    """Any JSON from B: scalars first, then each nested object or list of rows as its own table."""
    out = [f"## {title}", ""]
    if isinstance(data, list):
        data = {"rows": data}
    scalars = [[k, v] for k, v in data.items() if not isinstance(v, (dict, list))]
    if scalars:
        out += table(["Measure", "Value"], scalars) + [""]
    for k, v in data.items():
        if isinstance(v, dict):
            out += [f"**{k}**", ""] + table(["Measure", "Value"], [[a, b] for a, b in v.items()]) + [""]
        elif isinstance(v, list) and v and all(isinstance(r, dict) for r in v):
            cols = list(dict.fromkeys(c for r in v for c in r))
            out += [f"**{k}** ({len(v)} rows{', first ' + str(MAX_ROWS) if len(v) > MAX_ROWS else ''})", ""]
            out += table(cols, [[r.get(c) for c in cols] for r in v[:MAX_ROWS]]) + [""]
        elif isinstance(v, list):
            out += [f"**{k}**: {cell(v)}", ""]
    return out


def ms(v) -> str:
    return "–" if v is None else f"{v / 1000:.2f} s"


def a_section(r: dict) -> list[str]:
    d, n, t = r["director"], r["numbers"], r["templates"]
    lift = r["spoiler_lift"]
    out = [f"## Commentary and Director (Person A, {r['cut']} cut, generated {r['generated']})", "",
           f"Voice: `{r['voice']}`. Director: `{d['name']}` on the {d['engine']} workflow "
           f"(Director → Commentator → Verifier → TTS), replies recorded {d['recorded'] or '–'}.", ""]
    out += table(["Measure", "Value", "Target / note"], [
        ["Spoiler leaks", r["spoiler_leaks"], "0 (file 43 spoiler_leaks())"],
        ["Spoiler lift", lift.get("lift"),
         f"P(goal | build-up) {lift.get('p_goal_given_build')} vs mean xG {lift.get('mean_xg')}, n = {lift.get('n')}. "
         + (lift.get("note") or "")],
        ["Lines passing truth_check", f"{r['truth_check_pass']}/{r['lines']}", "100%"],
        ["Spoken numbers verified", f"{n['claims_verified']}/{n['claims']} ({n['pct_verified']}%)",
         f"{n['items']} lines state a score or the clock"],
        ["Template lines", f"{t['template_lines']}/{r['lines']} (LLM lines: {t['llm_lines']})", t["note"]],
        ["Lines on a shorter fallback text", f"{t['shorter_text']} ({t['shorter_text_pct']}%)",
         f"by kind: {cell(t['shorter_text_by_kind'])}"],
        ["Director windows / calls", f"{d['windows']} / {d['calls']}", "one window per shot; ≤ 1 call per 10 s"],
        ["Director plans from the model", d["model_plans"], ""],
        ["Fallbacks to the rules Director", d["fallbacks"],
         f"after a model call: {d['fallbacks_after_a_call']}; reasons: {cell(d['fallback_reasons']) if d['fallback_reasons'] else 'none'}"],
        ["Tokens per Director call", d["tokens_per_call"], "≤ 1,200 (file 43 §4)"],
    ]) + [""]
    out += ["**Director plan per window** (the rules plan alongside, for the A/B listen)", ""]
    out += table(["Shot", "t (s)", "Director", "Plan: level / lead / hold / hint", "Rules plan", "Build-up spoken"],
                 [[w["key"], w["t_shot"], w["director"], _plan(w["plan"]), _plan(w["rules_plan"]),
                   w["spoken_build_line"] or "(no build-up)"] for w in d["windows_detail"]]) + [""]

    fe = r.get("foundry_eval")
    out += ["**Numeric truth as a Foundry custom evaluator** (code-based, preview)", ""]
    if not fe:
        out += ["Not run yet: `python -m audiostands.eval --foundry-eval`. The same grader ran locally (above).", ""]
    elif fe.get("where") == "foundry":
        rc = fe.get("result_counts") or {}
        out += [f"Ran on Foundry {fe['measured']}: evaluator `{fe['evaluator']}`, run status **{fe['status']}**, "
                f"{rc.get('passed', '?')}/{rc.get('total', '?')} items passed ({rc.get('failed', 0)} failed, "
                f"{rc.get('errored', 0)} errored)." + (f" [Report]({fe['report_url']})" if fe.get("report_url") else ""),
                ""]
    else:
        out += [f"Not run on Foundry ({fe.get('reason')}); the same grader ran locally (above).", ""]

    out += ["**Real-time latency: plan → verify → TTS for each build-up, against the D − lead_s budget**", ""]
    rts = r.get("realtime") or []
    if not rts:
        out += ["Not measured yet: `python -m audiostands.eval --realtime` (needs Azure).", ""]
    else:
        out += table(["Measured", "Waits", "Build-ups (runs)", "Within budget", "Budget", "p50 total", "p95 total",
                      "p50 plan / TTS", "p95 plan / TTS", "Max", "Fallbacks"],
                     [[x["measured"], "wall clock" if x["speed"] == 1 else f"÷{x['speed']:g}",
                       f"{x['build_lines']} ({x['runs']})", f"{x['within_budget']}/{x['build_lines']}",
                       " / ".join(ms(b) for b in x["budget_ms"]), ms(x["p50_ms"]["total_ms"]),
                       ms(x["p95_ms"]["total_ms"]), f"{ms(x['p50_ms']['plan_ms'])} / {ms(x['p50_ms']['tts_ms'])}",
                       f"{ms(x['p95_ms']['plan_ms'])} / {ms(x['p95_ms']['tts_ms'])}", ms(x["max_total_ms"]),
                       x["director_fallbacks"]] for x in rts]) + [""]
        out += ["\"Waits ÷N\" shortens only the idle time between shots; every measured step runs at real speed. "
                "Each run opens its connections with one untimed warm-up call first, as a live service would "
                "before kick-off. Nearest-rank percentiles; with this few build-ups p95 is close to the maximum.", ""]
    out += qa_latency_section(r.get("qa_latency"))
    return out


def qa_latency_section(q: dict | None) -> list[str]:
    out = ["**Live spoken questions (Stage 7): end of the fan's speech → first answer audio**", ""]
    if not q:
        return out + ["Not measured yet: `python eval/qa_latency.py run …` then `summarise` (needs the deployed relay).", ""]
    out += table(["Measured", "Questions (answered)", "p50", "p95", "Max", "p50 / p95 to the facts", "Client p50 / p95",
                  "Tool calls", "Spoiler hits", "Model / voice"],
                 [[q["measured"], f"{q['questions']} ({q['answered']})", ms(q["p50_ms"]), ms(q["p95_ms"]),
                   ms(q["max_ms"]), f"{ms(q.get('facts_p50_ms'))} / {ms(q.get('facts_p95_ms'))}",
                   f"{ms(q['client_p50_ms'])} / {ms(q['client_p95_ms'])}", q["tool_calls"], q["spoiler_hits"],
                   f"{', '.join(q['model'])} / {', '.join(q['voice'])}"]]) + [""]
    out += [f"Outcomes: {cell(q['outcomes'])}. Latency is measured in the relay ({q['definition']}). "
            f"\"To the facts\" runs to the first audio after the tool results went back, so a short \"Let me check\" "
            f"preamble doesn't flatter it. No target; for comparison only, a rival's median is {q['rival_median_s']} s "
            "(file 42). Golden turns: " + ", ".join(f"`{f}`" for f in q["files"]) + ". Nearest-rank percentiles.", ""]
    if q["spoiler_hit_list"]:
        out += table(["Case", "Words", "Answer"], [[h["case_id"], ", ".join(h["words"]), h["answer"]]
                                                   for h in q["spoiler_hit_list"]]) + [""]
    return out


def _plan(p: dict | None) -> str:
    return "–" if not p else f"{p['build_up_level']:g} / {p['lead_s']:g} s / {p['hold_ms']} ms / {p['hint_type']}"


def build(here: Path = HERE) -> str:
    a, qa, listening = load(here / "report.json"), load(here / "qa.json"), load(here / "listening.json")
    out = ["# Audio Stands: evaluation report", "",
           "_Generated by `eval/build_report.py` from `eval/report.json` (A), `eval/qa.json` and `eval/listening.json` "
           "(B). Do not edit by hand: rerun the script._", ""]
    out += a_section(a) if a else ["## Commentary and Director (Person A)", "",
                                   "Missing: `eval/report.json`. Run `python -m audiostands.eval --cut judge`.", ""]
    out += generic(qa, "Q&A eval (Person B, eval/qa.json)") if qa is not None else [
        "## Q&A eval (Person B)", "", "Not yet: `eval/qa.json` is not in the repo.", ""]
    out += generic(listening, "Listening test (Person B, eval/listening.json)") if listening is not None else [
        "## Listening test (Person B)", "", "Not yet: `eval/listening.json` is not in the repo.", ""]
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    text = build()
    (HERE / "report.md").write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {HERE / 'report.md'} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
