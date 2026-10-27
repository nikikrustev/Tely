"""Machine-readable Render output (Tier 2 item 12, D37): the timed cue track as JSON and WebVTT, in every language.

    python -m tely.render_out --cut judge

The brief's Render stage asks for "clean, timed, machine-readable output that can drive synchronised graphic
overlays". The audio is one renderer of it; these files let any other one (a broadcast graphics system, a caption
encoder, a braille display) take the same verified lines at the same times:
    overlays.json             one record per line: in/out times, match clock, kind, priority, layout/anchor/metric,
                              the score at that moment, the text in every language, the verifier's verdicts
    descriptions.<lang>.vtt   the verified lines in that language (English keeps captions_sdh.vtt too)
Everything comes from the committed cue files; nothing is generated here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tely.commentary.captions import descriptions
from tely.commentary.source import BUNDLE, load_match

FILE = "overlays.json"


def _cues(out_dir: Path, lang: str) -> list[dict]:
    p = out_dir / f"cues.{lang}.radio.jsonl"
    return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()] if p.is_file() else []


def overlays(out_dir: Path, m) -> dict:
    langs = sorted({p.name.split(".")[1] for p in out_dir.glob("cues.*.radio.jsonl")}, key=lambda x: (x != "en", x))
    by_lang = {lang: {c["cue_id"]: c for c in _cues(out_dir, lang)} for lang in langs}
    rows = []
    for c in _cues(out_dir, "en"):
        score = m.score_at(c["t_in"])
        rows.append({
            "cue_id": c["cue_id"], "t_in": c["t_in"], "t_out": round(c["t_in"] + c["utterance"]["duration_ms"] / 1000, 3),
            "match_clock": c["match_clock"], "tc_in": c["tc_in"], "kind": c["kind"], "priority": c["priority"],
            "layout": c["layout"], "anchor": c["anchor"], "metric": c["metric"], "reveal": c["reveal"],
            "score": {m.team_name("home"): score["home"], m.team_name("away"): score["away"]},
            "text": {lang: by_lang[lang][c["cue_id"]]["text"]["radio"] for lang in langs if c["cue_id"] in by_lang[lang]},
            "evidence": c["evidence"], "truth_check": c["truth_check"], "spoiler_check": c["spoiler_check"],
        })
    return {"format": "tely.overlays/1", "match_id": m.meta["match"]["id"], "synthetic": True, "languages": langs,
            "time_base": "seconds of match time (t_in, t_out); tc_in is the broadcast timecode", "cues": rows}


def write(cut: str, out_dir: Path) -> list[Path]:
    m = load_match(cut)
    body = overlays(out_dir, m)
    out = [out_dir / FILE]
    out[0].write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for lang in body["languages"]:
        if lang == "en":
            continue
        p = out_dir / f"descriptions.{lang}.vtt"
        p.write_text(descriptions(_cues(out_dir, lang)), encoding="utf-8", newline="\n")
        out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    from tely import build_bundle

    ap = argparse.ArgumentParser(description="Timed cue track as JSON and WebVTT, every language")
    ap.add_argument("--cut", default="judge")
    args = ap.parse_args(argv)
    out_dir = BUNDLE / args.cut
    files = write(args.cut, out_dir)
    old = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    man = build_bundle.manifest(args.cut, out_dir, load_match(args.cut), old["voice"], old.get("director"))
    (out_dir / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"PASS: {', '.join(p.name for p in files)}; {man['files']} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
