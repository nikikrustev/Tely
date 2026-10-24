# OWNER: A (potencialbg). Stage 9a: the video's captions come from the judge cut, and every number the voiceover says
# is still true in eval/report.json or the bundle (BUILD_PLAN Stage 9: no number on screen that isn't in them).
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / "web" / "public" / "replay" / "v1" / "judge"


@pytest.fixture(scope="module")
def mc():
    spec = importlib.util.spec_from_file_location("make_captions", ROOT / "video" / "make_captions.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_committed_captions_are_current(mc):
    assert (ROOT / "video" / "captions_sdh.srt").read_text(encoding="utf-8") == mc.build(), \
        "run: python video/make_captions.py"


def test_captions_fit_the_video_and_are_ordered(mc):
    entries = mc.read_srt(ROOT / "video" / "captions_sdh.srt")
    assert entries and all(a < b <= mc.MAX_S for a, b, _ in entries)
    assert [a for a, _, _ in entries] == sorted(a for a, _, _ in entries)


def test_match_captions_are_the_cue_text_and_sounds(mc):
    text = " ".join(t for _, _, t in mc.match_captions())
    assert "Navy coming... Olvholm... here's a chance!" in text and "The goal stands! Goal for Navy!" in text
    assert "[crowd rises]" in text and "[Navy end roars]" in text and "[shot, left]" in text
    for v0, a, b in mc.EDIT:   # no commentary line is cut mid-word by the edit
        for line in (BUNDLE / "cues.en.radio.jsonl").read_text(encoding="utf-8").splitlines():
            c = json.loads(line)
            t0, t1 = c["t_in"], c["t_in"] + c["ttl_ms"] / 1000
            assert t1 <= a or t0 >= b or (a <= t0 and t1 <= b), c["cue_id"]


def test_voiceover_numbers_match_the_report(mc):
    vo = " ".join(t for _, _, t in mc.read_srt(ROOT / "video" / "voiceover.srt"))
    report = json.loads((ROOT / "eval" / "report.json").read_text(encoding="utf-8"))
    manifest = json.loads((BUNDLE / "manifest.json").read_text(encoding="utf-8"))
    assert "seventy lines, zero spoiler leaks, every number verified" in vo
    assert report["lines"] == 70 and report["spoiler_leaks"] == 0 and report["numbers"]["pct_verified"] == 100.0
    assert "four seconds before the header" in vo
    hero = next(w for w in report["director"]["windows_detail"] if w["key"] == "e00675")
    assert hero["plan"]["lead_s"] == 4.0
    assert "hears ten seconds ahead" in vo and manifest["delay_s"] == 10.0
    assert len(vo.split()) <= 255   # file 14: about 255 words is the ceiling for 1:52
