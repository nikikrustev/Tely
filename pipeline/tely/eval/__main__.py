"""python -m tely.eval --cut judge [--realtime] [--foundry-eval]  ->  eval/report.json.

Sections that need Azure (realtime, foundry_eval, qa_latency) are kept from the previous report.json when not re-run, with
the date they were measured, so a quick offline re-run never erases a measurement.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from tely.build_bundle import dir_env, recorded
from tely.commentary.source import ROOT, load_match
from tely.commentary.ssml import DEFAULT_VOICE
from tely.commentary.tts import load_env
from tely.eval import metrics, numeric_truth

REPORT = ROOT / "eval" / "report.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 5 eval: writes eval/report.json")
    ap.add_argument("--cut", default="judge")
    ap.add_argument("--out", type=Path, default=REPORT)
    ap.add_argument("--realtime", action="store_true", help="(b) live Director + TTS at wall-clock speed (Azure)")
    ap.add_argument("--speed", type=float, default=1.0, help="realtime: divide the idle waits by this")
    ap.add_argument("--repeat", type=int, default=1, help="realtime: play the cut this many times")
    ap.add_argument("--foundry-eval", action="store_true", help="(c) also run the grader as a Foundry evaluator")
    args = ap.parse_args(argv)

    env = load_env()
    voice = env.get("TTS_VOICE") or DEFAULT_VOICE
    m = load_match(args.cut)
    old = json.loads(args.out.read_text(encoding="utf-8")) if args.out.is_file() else {}
    today = time.strftime("%Y-%m-%d")
    rep = {"stage": 5, "generated": today, "voice": voice, **metrics.report(m, args.cut, voice, recorded(args.cut))}

    rep["foundry_eval"] = old.get("foundry_eval")
    if args.foundry_eval:
        items = numeric_truth.dataset(m, metrics.load_cues(args.cut))
        rep["foundry_eval"] = {"measured": today, **numeric_truth.run_foundry(items, dir_env(env))}

    rep["qa_latency"] = old.get("qa_latency")   # Stage 7, written by eval/qa_latency.py (needs a live relay)
    from tely.eval import realtime

    rep["realtime"] = [realtime.resummarise(r) for r in old.get("realtime") or []]   # kept rows, current summary
    if args.realtime:
        from tely.agents import tracing
        from tely.agents.director import FoundryDirector
        from tely.commentary.tts import AzureSynthesiser

        traces = tracing.setup(dir_env(env))
        try:
            model = FoundryDirector(dir_env(env))
            res = asyncio.run(realtime.harness(m, model, AzureSynthesiser(env), voice, args.speed, args.repeat))
        finally:
            tracing.flush()
        res = {"measured": time.strftime("%Y-%m-%d %H:%M"), "director": model.name, "traces": traces, **res}
        # one entry per speed: a new measurement at the same speed replaces the old one
        rep["realtime"] = [r for r in rep["realtime"] if r.get("speed") != args.speed] + [res]
        print(f"realtime x{args.speed}: {res['build_lines']} build lines, {res['within_budget']} within "
              f"{res['budget_ms']} ms; p50 {res['p50_ms']['total_ms']} ms, p95 {res['p95_ms']['total_ms']} ms")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    d = rep["director"]
    print(f"spoiler leaks {rep['spoiler_leaks']}, numbers {rep['numbers']['claims_verified']}/"
          f"{rep['numbers']['claims']} verified, truth_check {rep['truth_check_pass']}/{rep['lines']}, "
          f"Director {d['calls']} calls / {d['fallbacks']} fallbacks -> {args.out}")
    return 1 if rep["spoiler_leaks"] else 0


if __name__ == "__main__":
    sys.exit(main())
