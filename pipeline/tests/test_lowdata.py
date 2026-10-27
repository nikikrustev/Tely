"""D36: every commentary line's low-data copy is the same SSML in a smaller format, and never runs longer."""
import json

from tely.commentary import lowdata as LD
from tely.commentary.source import BUNDLE

OUT = BUNDLE / "judge"


def test_every_line_has_a_low_data_copy_of_the_same_ssml_and_it_fits():
    rep = json.loads((OUT / "lowdata.json").read_text(encoding="utf-8"))
    assert rep["format"] == LD.LOW_FMT
    for t in rep["tracks"]:
        cues = [json.loads(s) for s in (OUT / f"cues.{t['lang']}.radio.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
        idx = json.loads((OUT / "audio" / t["lang"] / LD.FOLDER / "index.json").read_text(encoding="utf-8"))
        assert t["no_ssml"] == t["too_long"] == 0 and t["bytes_low"] < t["bytes_normal"]
        for c in cues:
            sha = c["utterance"]["ssml_sha256"]
            assert LD.rebuild_ssml(c) is not None, c["cue_id"]
            assert sha in idx and (OUT / "audio" / t["lang"] / LD.FOLDER / f"{sha}.mp3").is_file()
