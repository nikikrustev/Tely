# OWNER: A (potencialbg). answers.py renders B's FRAGMENTS (Stage 6). Fake synthesiser: no Azure, CI-safe.
import json
import re
import shutil

import pytest

from audiostands import answers
from audiostands.commentary.source import MATCH_DIRS
from audiostands.commentary.ssml import DEFAULT_VOICE, build_ssml, ssml_sha256
from audiostands.qa import FRAGMENTS


class FakeSynth:
    def __init__(self):
        self.docs = []

    def synthesise(self, doc):
        self.docs.append(doc)
        return b"ID3" + doc.encode()[-16:], 1.25


@pytest.fixture()
def bundle_dir(tmp_path):
    for name in ("meta.json", "events.jsonl", "signals.json", "ticks.json.gz"):
        shutil.copyfile(MATCH_DIRS["judge"] / name, tmp_path / name)
    return tmp_path


def test_every_fragment_gets_a_clip_in_the_commentary_voice(bundle_dir):
    synth = FakeSynth()
    rep = answers.build(bundle_dir, lambda: synth)
    idx = json.loads((bundle_dir / "answers" / "index.json").read_text(encoding="utf-8"))
    frags = answers.fragments_for(bundle_dir)
    assert [f["id"] for f in frags] == [f["id"] for f in FRAGMENTS]  # a test copy gives B's committed list
    assert set(idx["fragments"]) == {f["id"] for f in frags} and idx["count"] == rep["fragments"] == len(frags)
    for f in frags:
        ssml = build_ssml(f["text"], answers.STYLES.get(f["id"], answers.STYLE), DEFAULT_VOICE)
        entry = idx["fragments"][f["id"]]
        assert entry == {"file": f"{ssml_sha256(ssml)}.mp3", "duration_ms": 1250}
        assert (bundle_dir / "answers" / entry["file"]).is_file()
    assert all(DEFAULT_VOICE in d for d in synth.docs)
    unique = {(answers.STYLES.get(f["id"], answers.STYLE), f["text"]) for f in frags}  # same SSML = one clip
    assert rep["tts_calls"] == rep["clips"] == len(unique) == len(synth.docs)
    assert rep["chars_text"] == sum(len(t) for _, t in unique) and rep["chars_total"] == sum(len(f["text"]) for f in frags)


def test_index_carries_no_text_so_it_cannot_spoil(bundle_dir):
    answers.build(bundle_dir, lambda: FakeSynth())
    raw = (bundle_dir / "answers" / "index.json").read_text(encoding="utf-8")
    for f in answers.fragments_for(bundle_dir):
        if f["id"].startswith(("ev_", "past_")):
            assert f["text"] not in raw


def test_rebuild_makes_no_tts_calls_and_is_byte_identical(bundle_dir):
    answers.build(bundle_dir, lambda: FakeSynth())
    before = {p.name: p.read_bytes() for p in (bundle_dir / "answers").iterdir()}
    rep = answers.build(bundle_dir, lambda: pytest.fail("must not connect when everything is cached"))
    assert rep["tts_calls"] == 0 and rep["chars_text"] == 0
    assert {p.name: p.read_bytes() for p in (bundle_dir / "answers").iterdir()} == before


def test_changed_text_renders_once_and_prunes_the_old_clip(bundle_dir):
    frags = [{"id": "hold", "text": "Hold that thought."}, {"id": "back", "text": "Back to the action."}]
    answers.build(bundle_dir, lambda: FakeSynth(), fragments=frags)
    frags[0] = {"id": "hold", "text": "Hold that thought, watch this!"}
    rep = answers.build(bundle_dir, lambda: FakeSynth(), fragments=frags)
    assert rep["tts_calls"] == 1 and rep["pruned"] == 1
    mp3s = {p.name for p in (bundle_dir / "answers").glob("*.mp3")}
    idx = json.loads((bundle_dir / "answers" / "index.json").read_text(encoding="utf-8"))
    assert mp3s == {v["file"] for v in idx["fragments"].values()}
    cache = json.loads((bundle_dir / "answers" / "cache.json").read_text(encoding="utf-8"))
    assert {f"{k}.mp3" for k in cache} == mp3s


def test_hold_says_that_not_what():
    hold = next(f for f in FRAGMENTS if f["id"] == "hold")
    assert not re.search(r"goal|shot|save|score|penalty|card", hold["text"], re.I)
