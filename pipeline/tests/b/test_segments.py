# OWNER: B (Nikolay). Stage 2 segments: deterministic, no cues (TEAM_SPLIT.md), and callable the way A's
# build_bundle calls it: build_segments.build(cut, out_dir).
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from tely import build_segments

ROOT = Path(__file__).resolve().parents[3]
JUDGE = ROOT / "web" / "public" / "replay" / "v1" / "judge"
INPUTS = ("meta.json", "events.jsonl", "signals.json", "ticks.json.gz")


def test_committed_segments_match_a_fresh_build(tmp_path):
    # SEAM(B->A): A's build_bundle reruns build_segments after build_match; any byte change would show in A's commits
    for name in INPUTS:
        shutil.copy(JUDGE / name, tmp_path / name)
    out = build_segments.build("judge", tmp_path)
    assert out == tmp_path / "segments.json"
    assert hashlib.sha256(out.read_bytes()).digest() == hashlib.sha256((JUDGE / "segments.json").read_bytes()).digest()


def test_segments_shape():
    doc = json.loads((JUDGE / "segments.json").read_text(encoding="utf-8"))
    segs = doc["segments"]
    assert all("cues" not in s for s in segs)                       # A's track loads cues itself
    assert segs[0]["t0"] == doc["t0"] and segs[-1]["t1"] == doc["t1"]
    assert all(b["t0"] == a["t1"] for a, b in zip(segs, segs[1:]))
    assert all(len(s["ball"]) == build_segments.SEG_S * build_segments.BALL_HZ for s in segs)
    seconds = [x["t"] for s in segs for x in s["seconds"]]
    assert seconds == list(range(int(doc["t0"]), int(doc["t1"]) + 1))
    signals = json.loads((JUDGE / "signals.json").read_text(encoding="utf-8"))
    assert [o for s in segs for o in s["one_shots"]] == signals["crowd_one_shots"]
    assert [h for s in segs for h in s["haptics"]] == signals["haptics"]
    rows = {r["t"]: r for r in signals["per_second"]}
    assert all(x["score"] == rows[x["t"]]["score"] for s in segs for x in s["seconds"])
