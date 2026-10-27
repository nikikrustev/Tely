"""D27: the commentary in other languages. A fake translator and a fake synthesiser, so no Foundry or Speech call."""
import json

from tely.commentary import languages as L
from tely.commentary.ssml import ssml_sha256
from tely.qa.tools import LANGUAGES

PLAYERS = ["Nevford", "Olvholm"]


class FakeSynth:
    """Every render lasts 80 ms per character, slower lines (higher rate) proportionally shorter."""

    def __init__(self):
        self.calls = 0

    def synthesise(self, ssml):
        self.calls += 1
        rate = int(ssml.split('rate="+')[1].split("%")[0])
        text = ssml.split('%">')[1].split("<")[0]
        return b"mp3", len(text) * 0.08 / (1 + rate / 100)


def cue(i, t, text):
    return {"cue_id": f"c_{i:04d}", "t_in": t, "text": {"radio": text}, "evidence": ["e1"],
            "utterance": {"lang": "en-US", "voice": "x", "style": "calm", "intensity": 0.1, "ssml_sha256": "s",
                          "audio_url": "audio/en/radio/s.mp3", "duration_ms": 900, "stale_ms": 500}}


def test_languages_match_the_commentators_tool():
    assert set(L.LANGS) | {"en"} == set(LANGUAGES)
    for lang, (_, _, (home, away)) in L.LANGS.items():
        assert (home, away) == LANGUAGES[lang][1:3]


def test_ssml_speaks_the_locale_in_the_one_multilingual_voice():
    ssml = L.build_ssml("Hola & adiós", "es-ES", 0.95, extra_rate=100)
    assert 'voice name="en-US-BrianMultilingualNeural"' in ssml and '<lang xml:lang="es-ES">' in ssml
    assert f'rate="+{L.MAX_RATE}%"' in ssml and "Hola &amp; adiós" in ssml   # capped, and escaped


def test_check_keeps_numbers_and_names_and_rejects_english_words():
    assert L.check("Nevford scores, 2 goals.", "Nevford marca, 2 goles.", PLAYERS) == []
    assert L.check("Nevford scores, 2 goals.", "Marca, dos goles.", PLAYERS) == ["number 2 missing", "name Nevford missing"]
    assert L.check("Reds nil, Navy one.", "Rojos nil, Azules one.", PLAYERS) == ["English word 'nil' left", "English word 'one' left"]
    assert L.check("Sixty minutes played.", "Soixante minutes jouées.", PLAYERS) == []   # French "minutes" is French


def test_translations_come_from_the_cache_and_only_missing_lines_go_to_the_model(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "L10N", tmp_path)
    asked = []

    class T:
        name = "fake@model"

        def translate(self, lang, lines):
            asked.append(list(lines))
            return [f"[{lang}] {s}" for s in lines]

    assert L.translations("de", ["Nevford.", "Olvholm."], PLAYERS, T)["Nevford."] == "[de] Nevford."
    L.translations("de", ["Nevford.", "Olvholm.", "Nevford again."], PLAYERS, T)
    assert asked == [["Nevford.", "Olvholm."], ["Nevford again."]]
    assert json.loads((tmp_path / "de.json").read_text(encoding="utf-8"))["translator"] == "fake@model"


def test_a_line_too_long_for_its_slot_is_sped_up_and_a_rebuild_renders_nothing(tmp_path):
    cues = [cue(1, 10.0, "short"), cue(2, 11.0, "long")]
    lines = {"short": "corto", "long": "una frase bastante larga para su hueco"}   # 38 chars: 3.0 s for a 0.85 s slot
    synth, measured = FakeSynth(), {}
    rep = L.build_lang(tmp_path, "es", cues, 30.0, lines, lambda: synth, measured)
    out = [json.loads(s) for s in (tmp_path / "cues.es.radio.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [c["t_in"] for c in out] == [10.0, 11.0] and out[0]["evidence"] == ["e1"]   # same times and facts
    assert out[0]["text"]["radio"] == "corto" and out[0]["utterance"]["lang"] == "es-ES"
    assert out[0]["utterance"]["audio_url"] == f"audio/es/radio/{out[0]['utterance']['ssml_sha256']}.mp3"
    assert rep["sped_up"] == 0 and rep["overlaps"] == 0    # the last line has until t_end
    first = L.build_ssml(lines["short"], "es-ES", 0.1)
    assert out[0]["utterance"]["ssml_sha256"] == ssml_sha256(first)
    # Now squeeze the first line: 0.4 s of room.
    cues = [cue(1, 10.0, "long"), cue(2, 10.55, "short")]
    synth2 = FakeSynth()
    rep = L.build_lang(tmp_path, "es", cues, 30.0, lines, lambda: synth2, measured)
    assert rep["sped_up"] == 1 and synth2.calls == 1     # the slow render was cached by the first build
    assert len(list((tmp_path / "audio" / "es" / "radio").glob("*.mp3"))) == 2   # the too-long first render is gone
    synth3 = FakeSynth()
    L.build_lang(tmp_path, "es", cues, 30.0, lines, lambda: synth3, measured)
    assert synth3.calls == 0
