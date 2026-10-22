"""Build the whole replay bundle for one cut, then write manifest.json. OWNER: A (potencialbg).

    python -m audiostands.build_bundle --cut judge

Order (BUILD_PLAN Stage 4, TEAM_SPLIT changes):
    1. B's build_match      -> meta.json, events.jsonl, signals.json, ticks.json.gz
    2. A's build_commentary -> cues.en.radio.jsonl, audio/en/radio/*.mp3, captions_sdh.vtt, descriptions.vtt
    3. B's build_segments   -> segments.json (B's Stage 2, on main since #7; skipped and reported if it is ever missing)
    4. manifest.json        -> file 43 §6 shape, with the sha256 of every file
Cues are NOT merged into segments.json: A's commentary track loads the cue file itself (TEAM_SPLIT.md).

B's files must come out byte-identical (TEAM_SPLIT.md "cross-lane rules"). This build snapshots them before and after:
- a .gz whose unzipped content is identical but whose bytes differ (another zlib build re-compressed it; contracts/b
  README) gets its original bytes written back, so git stays clean;
- any real content change exits 2: that is a determinism bug for B, and the changed files must not be committed.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Callable

from audiostands import build_commentary
from audiostands.commentary.source import BUNDLE, Match, load_match
from audiostands.commentary.ssml import DEFAULT_VOICE
from audiostands.commentary.tts import AzureSynthesiser, Synthesiser, TtsError, load_env

B_FILES = ("meta.json", "events.jsonl", "signals.json", "ticks.json.gz", "segments.json")
MAX_BYTES = 200 * 1024 * 1024   # BUILD_PLAN Stage 4; SWA Free allows 250 MB per environment (file 21)
MAX_FILES = 15_000              # SWA limit (file 21)
DELAY_S = 10.0                  # the broadcast delay D the look-ahead uses (files 39, 43)
CHAPTER_LEAD_S = 6.0            # a chapter starts this long before the build-up, so the rise is heard whole
AI_VOICE_NOTICE = "Commentary uses Azure AI voices. Match data is synthetic."


class DeterminismError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def b_snapshot(out_dir: Path) -> dict[str, bytes | None]:
    return {f: (out_dir / f).read_bytes() if (out_dir / f).is_file() else None for f in B_FILES}


def check_b_unchanged(out_dir: Path, before: dict[str, bytes | None]) -> list[str]:
    """Names of B's files whose content changed. Restores the original bytes of a gzip that only re-compressed."""
    changed = []
    for name, old in before.items():
        path = out_dir / name
        new = path.read_bytes() if path.is_file() else None
        if old is None or new == old:
            continue
        if name.endswith(".gz") and new is not None and gzip.decompress(new) == gzip.decompress(old):
            path.write_bytes(old)  # same data, different zlib: keep B's committed bytes
            continue
        changed.append(name)
    return changed


def run_b_match(cut: str, out_dir: Path) -> None:
    # SEAM(A->B): B's Stage 1 builder, called through its own entry points (pipeline/audiostands/build_match.py).
    from audiostands import build_match

    build_match.build(build_match.load_cut(), out_dir, report=False)


def run_b_segments(cut: str, out_dir: Path) -> str:
    # SEAM(A->B): B's Stage 2 segments builder, build(cut, out_dir) (pipeline/audiostands/build_segments.py, on main
    # since #7). The guards only matter if it is renamed or removed: the bundle then ships without segments.json.
    if importlib.util.find_spec("audiostands.build_segments") is None:
        return "skipped: audiostands.build_segments not found (B's Stage 2)"
    mod = importlib.import_module("audiostands.build_segments")
    builder = getattr(mod, "build", None)
    if builder is None:
        return "skipped: audiostands.build_segments has no build() (HANDOFF to B)"
    builder(cut, out_dir)
    return "built"


def chapters(cues: list[dict], m: Match) -> list[dict]:
    """"Next big moment" stops. Spoiler-safe: one before every build-up (goal or not) and every card, all named alike."""
    moments = sorted({c["t_in"] for c in cues if c["kind"] == "build"} |
                     {c["t_in"] for c in cues if c["kind"] == "foul" and c["haptic"]["tacton"] in ("yellow", "red")})
    return [{"t": round(max(m.t_start, t - CHAPTER_LEAD_S), 2), "label": f"Big moment {i}"}
            for i, t in enumerate(moments, 1)]


def manifest(cut: str, out_dir: Path, m: Match, voice: str) -> dict:
    cues_file = out_dir / f"cues.{build_commentary.LANG}.{build_commentary.LEVEL}.jsonl"
    cues = [json.loads(s) for s in cues_file.read_text(encoding="utf-8").splitlines() if s.strip()]
    files = sorted(p for p in out_dir.rglob("*") if p.is_file() and p.name != "manifest.json")
    rel = lambda p: p.relative_to(out_dir).as_posix()  # noqa: E731
    teams = m.meta["teams"]
    return {
        "bundle": "v1", "cut": cut, "match_id": m.meta["match"]["id"],
        "seed": m.meta["judge_cut"].get("seed"), "source": m.meta["judge_cut"].get("source"),
        "generator": m.meta.get("generator"), "format_version": m.meta.get("version"),
        "delay_s": DELAY_S, "t_start": m.t_start, "t_end": m.t_end, "duration_s": m.t_end - m.t_start,
        "clock_start": m.match_clock(m.t_start),
        "teams": {"H": teams["home"]["short_name"], "A": teams["away"]["short_name"]},
        "kits": {"H": teams["home"]["kit"]["words"], "A": teams["away"]["kit"]["words"]},
        "chapters": chapters(cues, m),
        "tracks": {"en": {"radio": cues_file.name}},
        "voice": voice,
        "meta": "meta.json", "events": "events.jsonl", "signals": "signals.json", "ticks": "ticks.json.gz",
        "segments": "segments.json" if (out_dir / "segments.json").is_file() else None,
        "captions": "captions_sdh.vtt", "descriptions": "descriptions.vtt",
        "answers": None,  # Stage 6 (A6) adds answers/index.json
        "ai_voice_notice": AI_VOICE_NOTICE,
        "files": len(files), "bytes": sum(p.stat().st_size for p in files),
        "sha256": {rel(p): sha256(p) for p in files},
    }


def build(cut: str, out_dir: Path, synth_factory: Callable[[], Synthesiser], voice: str = DEFAULT_VOICE,
          *, run_match: Callable[[str, Path], None] = run_b_match,
          run_segments: Callable[[str, Path], str] = run_b_segments) -> dict:
    before = b_snapshot(out_dir)
    run_match(cut, out_dir)
    changed = check_b_unchanged(out_dir, before)
    if changed:
        raise DeterminismError(f"B's files changed after build_match: {changed}. Don't commit them; tell B.")
    commentary = build_commentary.build(cut, out_dir, synth_factory, voice)
    segments = run_segments(cut, out_dir)
    man = manifest(cut, out_dir, load_match(cut), voice)
    if man["bytes"] > MAX_BYTES or man["files"] > MAX_FILES:
        raise RuntimeError(f"bundle too big: {man['bytes']} bytes in {man['files']} files "
                           f"(limits {MAX_BYTES} bytes, {MAX_FILES} files)")
    body = json.dumps(man, indent=1, ensure_ascii=False) + "\n"
    (out_dir / "manifest.json").write_text(body, encoding="utf-8", newline="\n")
    return {"commentary": commentary, "segments": segments, "files": man["files"], "bytes": man["bytes"],
            "chapters": man["chapters"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the replay bundle (match, commentary, segments, manifest)")
    ap.add_argument("--cut", default="judge", choices=["judge"])
    ap.add_argument("--voice", help="default: TTS_VOICE from .env")
    args = ap.parse_args(argv)
    env = load_env()
    voice = args.voice or env.get("TTS_VOICE") or DEFAULT_VOICE
    try:
        rep = build(args.cut, BUNDLE / args.cut, lambda: AzureSynthesiser(env), voice)
    except DeterminismError as exc:
        print(f"DETERMINISM BUG: {exc}")
        return 2
    except TtsError as exc:
        print(f"FAIL: {exc}")
        return 1
    c = rep["commentary"]
    ok = not c["failed"] and not c["spoiler_leaks"]
    print(f"{'PASS' if ok else 'FAIL'}: commentary {c['lines']} lines, {c['tts_calls']} TTS calls, "
          f"truth_check {c['truth_check_pass']}, spoiler leaks {len(c['spoiler_leaks'])}; segments {rep['segments']}; "
          f"{rep['files']} files, {rep['bytes'] / 1e6:.1f} MB; {len(rep['chapters'])} chapters")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
