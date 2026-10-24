# OWNER: A (potencialbg). The lively commentary style (D21, file 48) and the local-test rename. The synthesiser is
# mocked. The rename here uses made-up names: real club and player names never enter the repo (.gitignore).
import json
import re

import pytest

from audiostands import build_commentary, spoiler
from audiostands.commentary import lively, planner
from audiostands.commentary.source import BUNDLE, load_match, rename

NAMES = {"venue": "Testfield", "teams": {"home": {"short_name": "Larks"}, "away": {"short_name": "Owls"}},
         "players": {"r9": {"first_name": "Ada", "last_name": "Quill"}, "n9": {"first_name": "Bo", "last_name": "Zebedee"}}}


class FakeSynth:
    def synthesise(self, doc: str):
        text = re.sub(r"<[^>]+>|\[\w+\]", "", doc)
        return b"ID3fake-mp3", planner.estimate(text, "", 0) * 1.15


@pytest.fixture(scope="module", params=["sample", "judge"])
def built(tmp_path_factory, request):
    out = tmp_path_factory.mktemp(f"lively-{request.param}")
    rep = build_commentary.build(request.param, out, lambda: FakeSynth(), style="lively", names=NAMES)
    cues = [json.loads(s) for s in (out / "cues.en.radio.jsonl").read_text(encoding="utf-8").splitlines()]
    return {"rep": rep, "cues": cues, "cut": request.param}


def test_lively_passes_the_same_truth_and_spoiler_gates(built):
    assert built["rep"]["failed"] == [] and built["rep"]["spoiler_leaks"] == []
    assert all(c["truth_check"] == "pass" and c["spoiler_check"] == "pass" for c in built["cues"])
    assert {c["source"]["templates"] for c in built["cues"]} == {lively.NAME}


def test_lively_still_labels_the_ai_and_gives_directions(built):
    assert built["cues"][0]["text"]["radio"].startswith("AI commentary")
    kits = next(c for c in built["cues"] if c["kind"] == "kits")["text"]["radio"]
    assert "to your right" in kits and "to your left" in kits


def test_rename_reaches_every_line_and_leaves_no_synthetic_team_name(built):
    text = " ".join(c["text"]["radio"] for c in built["cues"])
    assert "Larks" in text or "Owls" in text
    assert "Reds" not in text and "Navy " not in text.replace("Navy shirts", "").replace("navy shirts", "")


def test_lively_is_less_repetitive_than_radio_v1(built):
    """Fewer lines open with a bare zone label ("Midfield, far side, ...")."""
    if built["cut"] != "judge":
        pytest.skip("judge cut only")
    zone_first = [c for c in built["cues"] if re.match(r"(Defensive third|Midfield|Attacking third),", c["text"]["radio"])]
    assert len(zone_first) <= len(built["cues"]) // 5, [c["text"]["radio"] for c in zone_first]


def test_rename_copies_and_keeps_events():
    m = load_match("sample")
    r = rename(m, NAMES)
    assert r.team_name("home") == "Larks" and m.team_name("home") != "Larks"   # the original is untouched
    assert r.events is m.events and r.meta["match"]["venue"]["name"] == "Testfield"
    assert r.surname("r9") == "Quill" and r.players["r9"]["name"] == "Ada Quill"


def test_names_build_refuses_to_write_into_the_deployed_bundle(tmp_path):
    names = tmp_path / "x.local.json"
    names.write_text(json.dumps(NAMES), encoding="utf-8")
    assert build_commentary.main(["--names", str(names), "--out", str(BUNDLE / "judge")]) == 1

