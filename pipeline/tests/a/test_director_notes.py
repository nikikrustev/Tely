"""D33: the Director's notes in the bundle match the recorded run and wait for each shot's reveal."""
import json

from tely import director_notes as N
from tely.commentary.source import BUNDLE, load_match


def test_committed_notes_are_current_and_wait_for_the_reveal():
    out = BUNDLE / "judge"
    committed = json.loads((out / N.FILE).read_text(encoding="utf-8"))
    cues = [json.loads(s) for s in (out / "cues.en.radio.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
    m = load_match("judge")
    assert committed == N.notes(m, cues, json.loads((N.RECORDED / "judge.json").read_text(encoding="utf-8")))
    shots = {e["id"]: e for e in m.events if e["type"] == "shot"}
    for n in committed["notes"]:
        assert n["show_after"] == round(m.reveal_t(shots[n["key"]]), 2)
        assert "outcome" not in json.dumps(n) and n["plan_check"] == "pass"
