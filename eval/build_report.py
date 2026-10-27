"""Merge the eval numbers into eval/report.md. OWNER: A (potencialbg). Stdlib only, no Azure, no keys.

    python eval/build_report.py

Reads (TEAM_SPLIT.md "The seams" point 5):
    eval/report.json      A: spoiler firewall, numbers, Director, real-time latency (python -m tely.eval)
    eval/qa.json          B: Q&A eval questions through answer_text(), if present
    eval/listening.json   the eyes-closed listening test (python eval/score_listening.py), if present
qa.json has no fixed shape, so it is rendered generically: scalars in a table, nested objects one level deep, lists of
rows as a table. listening.json has its own section; with 0 participants it says "not run yet" and shows no numbers.
A missing file is reported as missing, never invented.

Writes eval/report.md, and eval/report.json with qa.json and listening.json merged in as "qa" and "listening".
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
        out += ["Not run yet: `python -m tely.eval --foundry-eval`. The same grader ran locally (above).", ""]
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
        out += ["Not measured yet: `python -m tely.eval --realtime` (needs Azure).", ""]
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


LISTEN_NOT_RUN = ("Not run yet: 0 participants in `eval/listening_test.csv`. The protocol is `eval/listening_test.md`; "
                  "enter each session in the CSV, then run `python eval/score_listening.py` and this script. No "
                  "numbers are shown until then.")


def listening_section(lt) -> list[str]:
    """The listening test (eval/score_listening.py). No participants: "not run yet" and no numbers at all.
    Moderated sessions first; self-run tester-mode volunteers (D19) in their own subsection, never mixed in."""
    out = ["## Eyes-closed listening test (eval/listening.json)", ""]
    if lt is None:
        return out + [LISTEN_NOT_RUN.replace("0 participants in", "no `eval/listening.json` from"), ""]
    if not isinstance(lt, dict) or "participants" not in lt:   # a free-form file from before score_listening.py
        return generic(lt, "Listening test (Person B, eval/listening.json)")
    sr = lt.get("self_run") or {}
    if not lt["participants"]:
        out += [LISTEN_NOT_RUN if not sr.get("participants") else
                "Moderated sessions: not run yet (0 moderated participants in `eval/listening_test.csv`, "
                "protocol `eval/listening_test.md`). The self-run results below are not a substitute.", ""]
    else:
        out += listening_body(lt)
    if sr.get("participants"):
        out += ["### Self-run, sighted volunteers (tester mode, `?test=1`)", "", f"**{sr['note']}**", ""]
        out += listening_body(sr)
    return out


def listening_body(lt: dict) -> list[str]:
    out: list[str] = []
    c, pr, pa, vip, ref = lt["conditions"], lt["preferred"], lt["paired"], lt["blind_or_partially_sighted"], lt["rnib_reference"]
    said = lambda d: ", ".join(f"{n} {k.replace('_', ' ')}" for k, n in d.items() if n)   # noqa: E731
    n = lt["participants"]
    out += [f"**{n} participant{'' if n == 1 else 's'}** ({said(lt['sight'])}; listened via {said(lt['listened_via'])}), "
            f"sessions {lt['sessions'] or '–'}, group A {lt['groups']['A']} / group B {lt['groups']['B']}. "
            f"{lt['scale_note']}", ""]
    out += table(["Condition", "Rated", "Scale mean (min–max), of 15", "Enjoyment / access / following, of 5",
                  "Probes right"],
                 [[name, x["n"],
                   "–" if x["scale_mean"] is None else f"{x['scale_mean']:g} ({x['scale_min']}–{x['scale_max']})",
                   " / ".join(cell(x[f"{k}_mean"]) for k in ("enjoy", "access", "follow")),
                   f"{x['probes_right']}/{x['probes_asked']}"
                   + ("" if x["probes_pct"] is None else f" ({x['probes_pct']:g}%)")]
                  for name, x in (("Commentary only", c["commentary"]), ("Full Tely", c["full"]))]) + [""]
    out += table(["Probe", "Commentary only", "Full Tely"],
                 [[k, x["commentary"], x["full"]] for k, x in lt["probes"].items()]) + [""]
    out += [f"Same person, both clips (n = {pa['n']}): full minus commentary only, mean "
            f"{cell(pa['mean_full_minus_commentary'])} points; full higher for {pa['full_higher']}, the same for "
            f"{pa['same']}, commentary only higher for {pa['commentary_higher']}. Would rather follow a match with: "
            f"full {pr['full']}, commentary only {pr['commentary']}, no preference {pr['none']}"
            + (f", not asked {pr['not asked']}" if pr["not asked"] else "")
            + f". Asked the commentator: {lt['ask']['tried']} tried ({lt['ask']['yes']} worked, "
            f"{lt['ask']['partly']} partly, {lt['ask']['no']} not).", ""]
    if vip["participants"]:
        out += [f"Blind or partially sighted participants only (n = {vip['participants']}): scale mean "
                f"{cell(vip['commentary']['scale_mean'])} commentary only, {cell(vip['full']['scale_mean'])} full.", ""]
    else:
        out += ["No blind or partially sighted participants: these are sighted people listening with their eyes "
                "closed, which is not evidence for blind fans (file 36).", ""]
    out += [f"For reference only: {ref['what']} scored {ref['score']:g}/{ref['out_of']} in {ref['source']}; "
            f"{ref['note']}. With this few people "
            "there is no significance test. Clip 1 has a goal and Clip 2 doesn't; the groups balance that only with "
            "an even number of people.", ""]
    out += ["**Per participant**", ""] + table(
        ["Participant", "Group", "Sight", "Listened via", "Scale: commentary / full", "Probes: commentary / full",
         "Would rather", "Ask worked"],
        [[r["participant"], r["group"], r["sight"], r["listened_via"],
          f"{cell(r['commentary_scale'])} / {cell(r['full_scale'])}",
          f"{cell(r['commentary_probes'])} / {cell(r['full_probes'])}", r["preferred"], r["ask_worked"]]
         for r in lt["rows"]]) + [""]
    if lt["quotes"]:
        out += ["**Quotes** (with consent, no names)", ""]
        out += [f"> \"{cell(q['quote'])}\" ({q['participant']}, {cell(q['sight'] or 'sight not said').replace('_', ' ')})"
                for q in lt["quotes"]] + [""]
    return out


def _plan(p: dict | None) -> str:
    return "–" if not p else f"{p['build_up_level']:g} / {p['lead_s']:g} s / {p['hold_ms']} ms / {p['hint_type']}"


def build(here: Path = HERE) -> str:
    a, qa, listening = load(here / "report.json"), load(here / "qa.json"), load(here / "listening.json")
    out = ["# Tely: evaluation report", "",
           "_Generated by `eval/build_report.py` from `eval/report.json` (A), `eval/qa.json` and `eval/listening.json` "
           "(B). Do not edit by hand: rerun the script._", ""]
    out += a_section(a) if a else ["## Commentary and Director (Person A)", "",
                                   "Missing: `eval/report.json`. Run `python -m tely.eval --cut judge`.", ""]
    out += generic(qa, "Q&A eval (Person B, eval/qa.json)") if qa is not None else [
        "## Q&A eval (Person B)", "", "Not yet: `eval/qa.json` is not in the repo.", ""]
    out += listening_section(listening)
    return "\n".join(out).rstrip() + "\n"


def merged(here: Path = HERE) -> dict | None:
    """report.json with B's two files merged in as "qa" and "listening" (None without a report.json)."""
    a = load(here / "report.json")
    if a is None:
        return None
    return {**a, "qa": load(here / "qa.json"), "listening": load(here / "listening.json")}


def main() -> int:
    text = build()
    (HERE / "report.md").write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {HERE / 'report.md'} ({len(text.splitlines())} lines)")
    rep = merged()
    if rep is not None:
        (HERE / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                                          newline="\n")
        print(f"merged qa.json and listening.json into {HERE / 'report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
