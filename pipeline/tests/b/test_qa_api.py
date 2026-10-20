# OWNER: B (Nikolay). Stub created by A in Stage 0. Checks only the API shape, so it keeps passing once B
# replaces the NotImplementedError bodies.
import inspect

from audiostands import qa


def test_qa_exports_the_seam_api():
    for name in qa.__all__:
        assert hasattr(qa, name), name


def test_eight_voice_live_function_tools():
    names = [t["name"] for t in qa.TOOL_SCHEMAS]
    assert len(names) == 8 and len(set(names)) == 8
    assert all(t["type"] == "function" for t in qa.TOOL_SCHEMAS)


def test_no_tool_lets_the_model_set_the_clock():
    for tool in qa.TOOL_SCHEMAS:
        assert "playhead_s" not in tool["parameters"]["properties"], tool["name"]


def test_playhead_is_keyword_only():
    for fn in (qa.call_tool, qa.answer_text):
        param = inspect.signature(fn).parameters["playhead_s"]
        assert param.kind is inspect.Parameter.KEYWORD_ONLY
