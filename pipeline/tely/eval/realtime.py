"""(b) Real-time harness: plays the cut at wall-clock speed, live Director + live TTS. OWNER: A (potencialbg).

File 43 §2: the Director first sees a shot when truth time reaches it, while the listener's playhead is D = 10 s
behind. The build-up line plays at shot - lead_s, so plan -> verify -> TTS has D - lead_s seconds (6 s at 4.0).
For every window this measures that chain, from the moment the shot enters the look-ahead to the moment its build-up
MP3 exists, against that budget. TTS goes to a fresh temporary cache each run, so every build-up is really
synthesised (no cache hits), and nothing is written to the bundle.

--speed shortens only the idle waits between shots; every measured step still runs at real speed. One untimed
warm-up call per run opens the model and Speech connections first, as a live service would before kick-off.
"""

from __future__ import annotations

import asyncio
import statistics
import tempfile
import time
from pathlib import Path
from typing import Callable

from tely.agents import workflow as W
from tely.commentary.source import Match
from tely.commentary.ssml import build_ssml, ssml_sha256
from tely.commentary.tts import Synthesiser, TtsCache
from tely.spoiler import D_S

WARMUP_LINE = "Tely warm-up."


def pct(xs: list[float], q: float) -> float | None:
    """Nearest-rank percentile (q in 0..100). None for no data."""
    if not xs:
        return None
    s = sorted(xs)
    k = max(0, min(len(s) - 1, round(q / 100 * len(s) + 0.5) - 1))
    return round(s[k], 1)


async def one_run(m: Match, model, synth: Synthesiser, voice: str, speed: float, run_no: int,
                  sleep: Callable[[float], object] = asyncio.sleep) -> list[dict]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="as_rt_") as tmp:
        cache = TtsCache(Path(tmp), lambda: synth)

        def render(d) -> tuple[str, int]:
            ssml = build_ssml(d.texts[0], d.style, voice, pause_after_ms=d.pause_ms)
            sha = ssml_sha256(ssml)
            return sha, cache.ensure(sha, ssml, d.texts[0])

        # Untimed warm-up: token fetch, TLS and the Speech websocket (a live service does this before kick-off).
        ws = W.windows(m)
        if model is not None and ws:
            try:
                await model.ask("warmup", ws[0].feat)
            except Exception:
                pass
        synth.synthesise(build_ssml(WARMUP_LINE, "calm", voice))

        start = time.perf_counter()
        runner = W.run_window
        if W.use_agent_framework():
            from tely.agents import af_workflow

            runner = af_workflow.run_window
        for w in ws:
            due = (w.t_shot - m.t_start) / speed
            wait = due - (time.perf_counter() - start)
            if wait > 0:
                await sleep(wait)
            t0 = time.perf_counter()
            s = await runner(m, w, model, render)
            total = (time.perf_counter() - t0) * 1000
            budget = (D_S - s.plan.lead_s) * 1000
            rows.append({"run": run_no, "key": w.key, "t_shot": round(w.t_shot, 2), "director": s.director,
                         "fallback": s.fallback, "build": s.draft is not None, "plan_ms": round(s.plan_ms, 1),
                         "verify_ms": round(s.verify_ms, 1), "tts_ms": round(s.tts_ms, 1), "total_ms": round(total, 1),
                         "budget_ms": round(budget), "within_budget": total <= budget,
                         "over_budget_ms": round(total - budget, 1) if total > budget else 0.0})
    return rows


def summarise(rows: list[dict], speed: float, repeat: int) -> dict:
    build = [r for r in rows if r["build"]]
    tot = [r["total_ms"] for r in build]
    return {
        "speed": speed, "runs": repeat, "windows": len(rows), "build_lines": len(build),
        "budget_ms": sorted({r["budget_ms"] for r in build}),
        "within_budget": sum(r["within_budget"] for r in build),
        "p50_ms": {k: pct([r[k] for r in build], 50) for k in ("plan_ms", "verify_ms", "tts_ms", "total_ms")},
        "p95_ms": {k: pct([r[k] for r in build], 95) for k in ("plan_ms", "verify_ms", "tts_ms", "total_ms")},
        "max_total_ms": max(tot) if tot else None,
        "mean_total_ms": round(statistics.fmean(tot), 1) if tot else None,
        "director_fallbacks": sum(r["fallback"] is not None for r in rows),
        "rows": rows,
    }


async def harness(m: Match, model, synth: Synthesiser, voice: str, speed: float = 1.0, repeat: int = 1) -> dict:
    rows = []
    for k in range(repeat):
        rows += await one_run(m, model, synth, voice, speed, k + 1)
    return summarise(rows, speed, repeat)
