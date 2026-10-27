# OWNER: B (Nikolay). Stub created by A in Stage 0. Checks only the API shape, so it keeps passing once B
# replaces the NotImplementedError bodies.
import inspect

from tely import qa


def test_qa_exports_the_seam_api():
    for name in qa.__all__:
        assert hasattr(qa, name), name


def test_eleven_voice_live_function_tools():
    names = [t["name"] for t in qa.TOOL_SCHEMAS]
    assert len(names) == 11 and len(set(names)) == 11
    assert all(t["type"] == "function" for t in qa.TOOL_SCHEMAS)


def test_no_tool_lets_the_model_set_the_clock():
    for tool in qa.TOOL_SCHEMAS:
        assert "playhead_s" not in tool["parameters"]["properties"], tool["name"]


def test_playhead_is_keyword_only():
    for fn in (qa.call_tool, qa.answer_text):
        param = inspect.signature(fn).parameters["playhead_s"]
        assert param.kind is inspect.Parameter.KEYWORD_ONLY


def test_set_preferences_has_two_detail_levels():
    """D30: "key moments only" or "full radio"; any other level is named back to the fan instead of "Done."."""
    schema = next(t for t in qa.TOOL_SCHEMAS if t["name"] == "set_preferences")["parameters"]["properties"]
    assert set(schema) == {"crowd_mix", "haptics", "detail"} and schema["detail"]["enum"] == ["key", "full"]
    b = qa.load_bundle()
    p = (b.t0 + b.t1) / 2
    key = qa.call_tool("set_preferences", {"detail": "key"}, playhead_s=p, bundle=b)
    assert key["prefs"] == {"detail": "key"} and key["say"].startswith("Key moments only")
    asked = qa.call_tool("set_preferences", {"verbosity": "calm"}, playhead_s=p, bundle=b)
    assert asked["prefs"] == {} and asked["say"].startswith("I can do key moments only")
    assert asked["fragments"] is None   # no offline clip claims it either
    both = qa.call_tool("set_preferences", {"verbosity": "describer", "haptics": "off"}, playhead_s=p, bundle=b)
    assert both["prefs"] == {"haptics": "off"} and both["say"].startswith("Done. I can do")
    assert qa.call_tool("set_preferences", {"crowd_mix": 0.4}, playhead_s=p, bundle=b)["say"] == "Done."
    assert 'detail "key"' in qa.PERSONA
