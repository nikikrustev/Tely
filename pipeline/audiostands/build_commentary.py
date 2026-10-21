"""Build the Radio commentary track for one cut: cues, HD-voice MP3s, captions. OWNER: A (potencialbg).

    python -m audiostands.build_commentary --cut judge

Writes into web/public/replay/v1/<cut>/:
    cues.en.radio.jsonl           one cue per line (file 43 §3 contract; SSML stripped, as by the release gate)
    audio/en/radio/<sha>.mp3      one MP3 per line, named by SSML sha256; index.json holds the real durations
    captions_sdh.vtt              words + crowd sounds
    descriptions.vtt              verified lines for the descriptions track
The planner runs again with the real MP3 durations until every placed line is rendered, so no two lines overlap.
A second build makes 0 TTS calls. The build fails (exit 1) if any line fails truth_check or spoiler_check.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

from audiostands import spoiler
from audiostands.commentary import captions, planner, verifier
from audiostands.commentary.source import BUNDLE, Match, load_match
from audiostands.commentary.ssml import DEFAULT_VOICE, build_ssml, ssml_sha256
from audiostands.commentary.tts import AzureSynthesiser, Synthesiser, TtsCache, TtsError, load_env

LANG, LEVEL = "en", "radio"
MAX_ROUNDS = 8


class BuildError(RuntimeError):
    pass


def tc(t: float, fps: int = 25) -> str:
    frames = round(t * fps)
    s, f = divmod(frames, fps)
    h, rem = divmod(s, 3600)
    mi, s = divmod(rem, 60)
    return f"{h:02d}:{mi:02d}:{s:02d}:{f:02d}"


def render_lines(m: Match, cache: TtsCache, voice: str) -> list[planner.Line]:
    """Plan, render whatever is missing, re-plan with real durations; stop when every placed line is cached."""
    def ssml_of(text: str, style: str, pause_ms: int) -> str:
        return build_ssml(text, style, voice, pause_after_ms=pause_ms)

    def duration_of(text: str, style: str, pause_ms: int) -> float:
        ms = cache.duration_ms(ssml_sha256(ssml_of(text, style, pause_ms)))
        return ms / 1000 if ms is not None else planner.estimate(text, style, pause_ms)

    for _ in range(MAX_ROUNDS):
        lines = planner.plan(m, duration_of)
        missing = [(ssml_of(ln.text, ln.draft.style, ln.draft.pause_ms), ln.text) for ln in lines]
        missing = [(s, t) for s, t in missing if not cache.has(ssml_sha256(s))]
        if not missing:
            return lines
        for ssml, text in dict.fromkeys(missing):
            cache.ensure(ssml_sha256(ssml), ssml, text)
    raise BuildError(f"plan did not settle in {MAX_ROUNDS} rounds")


def to_cue(m: Match, seq: int, ln: planner.Line, voice: str, cache: TtsCache) -> dict:
    d = ln.draft
    ssml = build_ssml(ln.text, d.style, voice, pause_after_ms=d.pause_ms)
    sha = ssml_sha256(ssml)
    sec = m.second(ln.t_in)
    ball = m.ball(ln.t_in)
    one_shot = [{"end": o["end"], "kind": o["kind"]} for o in m.signals.get("crowd_one_shots", [])
                if d.reveal == "outcome" and d.kind == "react" and abs(o["t"] - m.reveal_t(m.by_id(d.evidence[0]))) < 0.05]
    truth = verifier.truth_check(m, ln.text, ln.t_in, list(d.evidence))
    spoil = verifier.spoiler_check(m, ln.text, ln.t_in, list(d.evidence))
    return {
        "cue_id": f"c_{seq:04d}", "seq": seq, "match_id": m.meta["match"]["id"],
        "match_clock": m.match_clock(ln.t_in), "tc_in": tc(ln.t_in), "t_in": round(ln.t_in, 2),
        "ttl_ms": cache.duration_ms(sha), "priority": d.prio, "kind": d.kind, "reveal": d.reveal,
        "layout": "audio", "anchor": None, "metric": "tension",
        "text": {"radio": ln.text},
        "utterance": {"lang": "en-US", "voice": voice, "style": d.style, "intensity": round(d.intensity, 2),
                      "ssml_sha256": sha, "audio_url": f"audio/{LANG}/{LEVEL}/{sha}.mp3",
                      "duration_ms": cache.duration_ms(sha), "stale_ms": round(d.stale_s * 1000)},
        # SEAM(A->B): crowd and tension values are B's signals.json at t_in, copied, never recomputed.
        "crowd_state": {"H": sec["crowd"]["H"], "A": sec["crowd"]["A"], "one_shot": one_shot or None},
        "haptic": {"tacton": d.tacton, "team": d.team, "at_offset_ms": 0, "heartbeat_tension": sec["tension"]},
        "spatial": {"x": ball["x"], "y": ball["y"], "z": ball["z"], "earcon": None},
        "evidence": list(d.evidence),
        "truth_check": "pass" if not truth else "fail", "spoiler_check": "pass" if not spoil else "fail",
        "errors": truth + spoil,
        "source": {"cut": m.meta["judge_cut"].get("source"), "generator_seed": m.meta["judge_cut"].get("seed"),
                   "planner": "lookahead_v1", "templates": "radio_v1", "director": None},
    }


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8", newline="\n")


def build(cut: str, out_dir: Path, synth_factory: Callable[[], Synthesiser], voice: str = DEFAULT_VOICE) -> dict:
    m = load_match(cut)
    cache = TtsCache(out_dir / "audio" / LANG / LEVEL, synth_factory)
    lines = render_lines(m, cache, voice)
    cues = [to_cue(m, i + 1, ln, voice, cache) for i, ln in enumerate(lines)]
    failed = [(c["cue_id"], c["text"]["radio"], c["errors"]) for c in cues if c["errors"]]
    for c in cues:
        if not c["errors"]:
            del c["errors"]
    events = spoiler.flat_events(m)
    leaks = spoiler.spoiler_leaks(cues, events)
    _write(out_dir / f"cues.{LANG}.{LEVEL}.jsonl",
           "\n".join(json.dumps(c, ensure_ascii=False, separators=(",", ":")) for c in cues))
    _write(out_dir / "captions_sdh.vtt", captions.captions_sdh(cues, m))
    _write(out_dir / "descriptions.vtt", captions.descriptions(cues))
    referenced = {c["utterance"]["ssml_sha256"] for c in cues}
    return {
        "cut": cut, "match_source": str(m.src), "voice": voice, "lines": len(cues),
        "chars_spoken": sum(len(c["text"]["radio"]) for c in cues),
        "tts_calls": cache.calls, "chars_synthesised_text": cache.chars_text, "chars_synthesised_ssml": cache.chars_ssml,
        "unreferenced_mp3": len(set(cache.index) - referenced),
        "truth_check_pass": f"{sum(c['truth_check'] == 'pass' for c in cues)}/{len(cues)}",
        "spoiler_leaks": leaks, "spoiler_lift": spoiler.spoiler_lift(cues, events), "failed": failed,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the Radio commentary track (cues, MP3s, captions)")
    ap.add_argument("--cut", default="judge")
    ap.add_argument("--out", type=Path, help="default: web/public/replay/v1/<cut>")
    ap.add_argument("--voice", help="default: TTS_VOICE from .env")
    args = ap.parse_args(argv)
    env = load_env()
    voice = args.voice or env.get("TTS_VOICE") or DEFAULT_VOICE
    try:
        rep = build(args.cut, args.out or BUNDLE / args.cut, lambda: AzureSynthesiser(env), voice)
    except TtsError as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    ok = not rep["failed"] and not rep["spoiler_leaks"]
    print(f"{'PASS' if ok else 'FAIL'}: {rep['lines']} lines, {rep['tts_calls']} TTS calls, "
          f"{rep['chars_synthesised_text']} characters synthesised (SSML {rep['chars_synthesised_ssml']}), "
          f"truth_check {rep['truth_check_pass']}, spoiler leaks {len(rep['spoiler_leaks'])}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
