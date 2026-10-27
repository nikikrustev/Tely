"""Build the Radio commentary track for one cut: cues, HD-voice MP3s, captions.

    python -m tely.build_commentary --cut judge
    python -m tely.build_commentary --style lively --names pipeline/names/liverpool-arsenal.local.json

--style lively uses commentary/lively.py instead of templates.py (radio_v1). --names renames teams, players and venue
for a local listening test only; it then writes to web/.local/<names file stem>/ (git-ignored, never deployed, served
by the dev server at /replay/v1/local/<stem>/), never into the shipped bundle.

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

from tely import spoiler
from tely.commentary import captions, planner, verifier
from tely.commentary.source import BUNDLE, ROOT, Match, load_match, rename
from tely.commentary.ssml import DEFAULT_VOICE, build_ssml, ssml_sha256
from tely.commentary.tts import AzureSynthesiser, Synthesiser, TtsCache, TtsError, load_env

LANG, LEVEL = "en", "radio"
LOCAL = ROOT / "web" / ".local"  # git-ignored local test bundles (never deployed)
MAX_ROUNDS = 8


class BuildError(RuntimeError):
    pass


def tc(t: float, fps: int = 25) -> str:
    frames = round(t * fps)
    s, f = divmod(frames, fps)
    h, rem = divmod(s, 3600)
    mi, s = divmod(rem, 60)
    return f"{h:02d}:{mi:02d}:{s:02d}:{f:02d}"


def render_lines(m: Match, cache: TtsCache, voice: str, plans: dict | None = None) -> list[planner.Line]:
    """Plan, render whatever is missing, re-plan with real durations; stop when every placed line is cached."""
    def ssml_of(text: str, style: str, pause_ms: int) -> str:
        return build_ssml(text, style, voice, pause_after_ms=pause_ms)

    def duration_of(text: str, style: str, pause_ms: int) -> float:
        ms = cache.duration_ms(ssml_sha256(ssml_of(text, style, pause_ms)))
        return ms / 1000 if ms is not None else planner.estimate(text, style, pause_ms)

    for _ in range(MAX_ROUNDS):
        lines = planner.plan(m, duration_of, plans)
        missing = [(ssml_of(ln.text, ln.draft.style, ln.draft.pause_ms), ln.text) for ln in lines]
        missing = [(s, t) for s, t in missing if not cache.has(ssml_sha256(s))]
        if not missing:
            return lines
        for ssml, text in dict.fromkeys(missing):
            cache.ensure(ssml_sha256(ssml), ssml, text)
    raise BuildError(f"plan did not settle in {MAX_ROUNDS} rounds")


def to_cue(m: Match, seq: int, ln: planner.Line, voice: str, cache: TtsCache, director: str | None = None) -> dict:
    templates_name = getattr(planner.lines_for(m), "NAME", "radio_v1")
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
                   "planner": "lookahead_v1", "templates": templates_name,
                   # Stage 5: who planned this build-up's tension (file 43 §3 "source.director")
                   "director": director if d.kind == "build" else None},
    }


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8", newline="\n")


def build(cut: str, out_dir: Path, synth_factory: Callable[[], Synthesiser], voice: str = DEFAULT_VOICE,
          plans: dict | None = None, directors: dict[str, str] | None = None, style: str = "radio_v1",
          names: dict | None = None) -> dict:
    """plans / directors: shot id -> the Director's verified plan / its name (Stage 5). None: Stage 3 rules.
    style: "radio_v1" (templates.py) or "lively" (lively.py). names: a local test rename (source.rename)."""
    if style not in planner.STYLES:
        raise ValueError(f"unknown style {style!r}")
    m = load_match(cut)
    m.style = style  # type: ignore[attr-defined]
    if names:
        m = rename(m, names)
    cache = TtsCache(out_dir / "audio" / LANG / LEVEL, synth_factory)
    lines = render_lines(m, cache, voice, plans)
    directors = directors or {}
    cues = [to_cue(m, i + 1, ln, voice, cache, directors.get(ln.draft.evidence[0]) if ln.draft.evidence else None)
            for i, ln in enumerate(lines)]
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
    ap.add_argument("--style", default="radio_v1", choices=sorted(planner.STYLES))
    ap.add_argument("--names", type=Path, help="local test rename (JSON); output goes to web/.local/<stem>/")
    args = ap.parse_args(argv)
    env = load_env()
    voice = args.voice or env.get("TTS_VOICE") or DEFAULT_VOICE
    names = json.loads(args.names.read_text(encoding="utf-8")) if args.names else None
    out = args.out or (LOCAL / args.names.name.split(".")[0] if args.names else BUNDLE / args.cut)
    if names and BUNDLE in out.resolve().parents:
        print("FAIL: --names output must stay out of web/public (it would be deployed)")
        return 1
    try:
        rep = build(args.cut, out, lambda: AzureSynthesiser(env), voice, style=args.style, names=names)
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
