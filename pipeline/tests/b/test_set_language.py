"""set_language (D27): the fan asks for another language; the page and the relay switch, the match never changes."""
from tely import qa
from tely.qa.bundle import load_bundle
from tely.qa.tools import LANGUAGES

B = load_bundle()
P = (B.t0 + B.t1) / 2


def test_the_schema_offers_exactly_the_languages_we_recorded():
    schema = next(t for t in qa.TOOL_SCHEMAS if t["name"] == "set_language")["parameters"]["properties"]
    assert schema["language"]["enum"] == list(LANGUAGES) == ["en", "bg", "es", "ar", "fr", "de"]


def test_a_switch_confirms_in_the_new_language_and_sends_it_to_the_page():
    r = qa.call_tool("set_language", {"language": "bg"}, playhead_s=P, bundle=B)
    assert r["prefs"] == {"language": "bg"} and r["say"] == LANGUAGES["bg"][3]


def test_an_unknown_language_lists_the_ones_we_speak():
    r = qa.call_tool("set_language", {"language": "it"}, playhead_s=P, bundle=B)
    assert r["error"] == "unknown_language" and r["candidates"] == list(LANGUAGES)


def test_it_never_touches_the_match():
    before = qa.call_tool("get_score_and_clock", {}, playhead_s=P, bundle=B)
    qa.call_tool("set_language", {"language": "ar"}, playhead_s=P, bundle=B)
    assert qa.call_tool("get_score_and_clock", {}, playhead_s=P, bundle=B) == before


def test_the_persona_answers_a_switch_with_the_tools_sentence_only():
    # Seen live 27 Oct: "Claro, voy a cambiar el idioma... De momento no haré nada más. Seguimos la narración en español."
    assert "call set_language straight away, without\nsaying anything first" in qa.PERSONA
    assert "word for word, and nothing else" in qa.PERSONA
