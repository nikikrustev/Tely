"""Director's notes (Tier 1 item 9, D33): what the agents decided for each build-up, for sighted judges (?radar=1).

    python -m tely.director_notes --cut judge      # writes director_notes.json into the bundle, refreshes the manifest

One entry per Director window (one per shot): the plan the Foundry Director returned, what the rules Director would
have said, the model's latency and tokens, the Verifier's verdict on the plan and on the spoken build-up line.
`show_after` is the shot's reveal_t: the page shows an entry only once the playhead has passed it, so the panel can
never hint that a chance is coming (the spoiler clamp, D11). The entries hold no outcome: the Director never sees
one, and the shot's result is not copied in.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tely.agents import director as D
from tely.agents import rules_director
from tely.commentary.source import BUNDLE, Match, load_match

FILE = "director_notes.json"
RECORDED = Path(D.__file__).parent / "recorded"


def notes(m: Match, cues: list[dict], recorded: dict) -> dict:
    by_shot = {e["id"]: e for e in m.events if e["type"] == "shot"}
    builds = {ev: c for c in cues if c["kind"] == "build" for ev in c["evidence"]}
    out = []
    for call in recorded.get("calls", []):
        shot = by_shot.get(call["key"])
        if shot is None:
            continue
        feat = D.features(m, shot)
        try:
            plan, verdict = D.parse(call["raw"], feat).to_dict(), "pass"
        except D.PlanError as exc:   # the Verifier rejected it: the window fell back to rules
            plan, verdict = None, f"rejected: {exc}"
        line = builds.get(call["key"])
        out.append({
            "key": call["key"], "show_after": round(m.reveal_t(shot), 2), "clock": m.match_clock(m.t(shot)),
            "plan": plan, "rules_plan": rules_director.plan(feat).to_dict(), "plan_check": verdict,
            "latency_ms": round(call.get("latency_ms") or 0), "tokens": sum((call.get("tokens") or {}).values()) or None,
            "xg": feat["shot"]["xg"], "zone": feat["shot"]["zone"],
            "line": None if line is None else {"cue_id": line["cue_id"], "text": line["text"]["radio"],
                                                "truth_check": line["truth_check"], "spoiler_check": line["spoiler_check"]},
        })
    return {"director": recorded.get("director"), "notes": sorted(out, key=lambda n: n["show_after"])}


def write(cut: str, out_dir: Path) -> Path | None:
    rec = RECORDED / f"{cut}.json"
    if not rec.is_file():
        return None
    cues = [json.loads(s) for s in (out_dir / "cues.en.radio.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
    body = notes(load_match(cut), cues, json.loads(rec.read_text(encoding="utf-8")))
    path = out_dir / FILE
    path.write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return path


def main(argv: list[str] | None = None) -> int:
    from tely import build_bundle

    ap = argparse.ArgumentParser(description="Write the Director's notes into the bundle")
    ap.add_argument("--cut", default="judge")
    args = ap.parse_args(argv)
    out_dir = BUNDLE / args.cut
    if write(args.cut, out_dir) is None:
        print(f"FAIL: no recorded Director run for {args.cut}")
        return 1
    old = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    man = build_bundle.manifest(args.cut, out_dir, load_match(args.cut), old["voice"], old.get("director"))
    (out_dir / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"PASS: {FILE}, {man['files']} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
