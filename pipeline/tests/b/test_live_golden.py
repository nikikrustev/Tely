# OWNER: B (Nikolay). Regression tests from A's live Voice Live transcripts (contracts/golden/a/live_<date>.jsonl,
# TEAM_SPLIT.md seam 4): every tool call the real model made is replayed through B's tools at the same playhead.
# The tools are deterministic, so the answer must be identical, and it must never cite anything after the playhead.
# Skips until A commits the first transcript (A7). Reads the format tolerantly; see HANDOFF in the PR for the keys.
from __future__ import annotations

import json
from pathlib import Path

import pytest

from audiostands import qa
from audiostands.qa.bundle import load_bundle

ROOT = Path(__file__).resolve().parents[3]
FILES = sorted((ROOT / "contracts" / "golden" / "a").glob("live_*.jsonl"))
B = load_bundle()


def _maybe_json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return v
    return v


def tool_calls():
    """(case id, tool name, args, playhead_s, recorded result) for every tool call in every transcript line."""
    for f in FILES:
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            turn = json.loads(line)
            for j, call in enumerate(turn.get("tool_calls") or turn.get("calls") or []):
                name = call.get("name") or call.get("tool")
                args = _maybe_json(call.get("args", call.get("arguments", {}))) or {}
                p = call.get("playhead_s", turn.get("playhead_s"))
                result = _maybe_json(call.get("result", call.get("output")))
                yield f"{f.stem}:{i}:{j}:{name}", name, args, p, result


CALLS = list(tool_calls())


@pytest.mark.skipif(not FILES, reason="no live transcripts in contracts/golden/a/ yet (A7)")
@pytest.mark.parametrize("case", CALLS, ids=[c[0] for c in CALLS])
def test_live_tool_call_replays_identically_and_never_spoils(case):
    _, name, args, p, recorded = case
    assert p is not None, "transcript tool call has no playhead_s (HANDOFF to A)"
    now = qa.call_tool(name, args, playhead_s=p, bundle=B)
    if isinstance(recorded, dict) and "say" in recorded:
        assert now["say"] == recorded["say"], "tool answer changed since the live session"
        assert now.get("evidence_ids") == recorded.get("evidence_ids")
    sig = B.signals["events"]
    for eid in now.get("evidence_ids", []):
        if eid in sig:
            assert sig[eid]["t"] <= p and sig[eid]["reveal_t"] <= p, (name, eid, p)


def test_live_transcripts_hold_no_secrets():
    # TEAM_SPLIT seam 4: transcripts have no keys, tokens or audio.
    for f in FILES:
        text = f.read_text(encoding="utf-8").lower()
        for bad in ("api-key", "api_key", "authorization", "bearer ", "ocp-apim", "\"audio\":"):
            assert bad not in text, f"{f.name} contains {bad!r}"
