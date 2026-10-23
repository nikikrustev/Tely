# OWNER: B (Nikolay). Player names exactly as the live model passed them to our tools in A's golden turns
# (contracts/golden/a/live_2026-10-23.jsonl): it rewrites what the fan said ("Red keeper", "Gus Fenford #9") and
# speech-to-text mishears ("Tio" for "Teo"). Each must resolve to the right player, or to a short "which one?" list.
from __future__ import annotations

import json
from pathlib import Path

import pytest

from audiostands.qa import tools
from audiostands.qa.bundle import load_bundle

GOLDEN = Path(__file__).resolve().parents[3] / "contracts" / "golden" / "a" / "live_2026-10-23.jsonl"
B = load_bundle()

# name the model passed -> the one player it means, or the candidates to ask between
CASES = {
    "Gus Fenford #9": "Gus Fenford",                  # was "which number 9?": the name picks the Navy 9
    "Red keeper": "Omar Vaston",                      # was "which keeper?": "Red" is the Reds
    "Red Keeper": "Omar Vaston",
    "Reds #9": "Arlo Orlani",
    "Arlo Orlani (Reds #9)": "Arlo Orlani",
    "Gus Fenford (Navy #9)": "Gus Fenford",
    "Gus Fenford": "Gus Fenford",
    "Arlo Orlani": "Arlo Orlani",
    "Tio": ["Teo Dunwick", "Teo Varell", "Teo Ashard"],   # was 4 unrelated Reds players
    "Teo": ["Teo Dunwick", "Teo Varell", "Teo Ashard"],
    "9": ["Arlo Orlani", "Gus Fenford"],
    "goalkeeper": ["Omar Vaston", "Gus Galic"],
}


def _golden_players() -> set[str]:
    rows = [json.loads(s) for s in GOLDEN.read_text(encoding="utf-8").splitlines() if s.strip()]
    return {c["args"]["player"] for r in rows for c in r.get("tool_calls") or [] if "player" in (c.get("args") or {})}


def test_every_name_the_live_model_passed_is_covered():
    assert set(CASES) == _golden_players()


@pytest.mark.parametrize("name", sorted(CASES))
@pytest.mark.parametrize("tool", ["where_is", "get_player_stats"])
def test_live_model_names_resolve(name, tool):
    want = CASES[name]
    r = tools.call(tool, {"player": name}, 700.0, B)
    if isinstance(want, str):
        assert "error" not in r, r
        assert want in r["say"]
    else:
        assert r["error"] == "ambiguous_or_unknown_player"
        assert [c.split(" (")[0] for c in r["candidates"]] == want


@pytest.mark.parametrize("name, want", [("Fenford #7", None), ("Zorblax", []), ("Red's number 9", "Arlo Orlani"),
                                        ("Navy keeper", "Gus Galic")])
def test_names_beyond_the_golden_turns(name, want):
    r = tools.call("where_is", {"player": name}, 700.0, B)
    if isinstance(want, str):
        assert want in r["say"]
    elif want == []:
        assert r["candidates"] == []                  # an unknown name gets no random list to read out
    else:
        assert "error" in r and "Gus Fenford (Navy #9)" in r["candidates"]   # name and number disagree: ask
