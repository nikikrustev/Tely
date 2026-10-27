"""D37: the machine-readable Render output is current, complete and in every language."""
import json

from tely import render_out as R
from tely.commentary.source import BUNDLE, load_match

OUT = BUNDLE / "judge"


def test_overlays_are_current_and_every_line_has_every_language():
    committed = json.loads((OUT / R.FILE).read_text(encoding="utf-8"))
    assert committed == R.overlays(OUT, load_match("judge"))
    assert committed["synthetic"] is True and len(committed["cues"]) == 70
    for c in committed["cues"]:
        assert set(c["text"]) == set(committed["languages"]) and c["t_out"] > c["t_in"]
        assert c["truth_check"] == c["spoiler_check"] == "pass"


def test_a_description_track_per_translation():
    for lang in json.loads((OUT / R.FILE).read_text(encoding="utf-8"))["languages"]:
        if lang != "en":
            vtt = (OUT / f"descriptions.{lang}.vtt").read_text(encoding="utf-8")
            assert vtt.startswith("WEBVTT") and vtt.count(" --> ") >= 60
