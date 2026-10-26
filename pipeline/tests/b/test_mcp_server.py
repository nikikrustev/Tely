# OWNER: B (Nikolay). The Stats MCP server (qa/mcp_server.py): every tool clamps to the playhead the relay sends in the
# X-AudioStands-Playhead header, gives exactly the relay's answer (qa.call_tool), and the model can never set the clock.
# Real streamable-HTTP calls, served in memory (no network port).
from __future__ import annotations

import asyncio
import random

import pytest

pytest.importorskip("mcp", reason='pip install -e "pipeline[dev]"')
import httpx2  # noqa: E402  (comes with the MCP SDK)
from mcp import Client, ClientSession  # noqa: E402
from mcp.client.streamable_http import streamable_http_client  # noqa: E402

from audiostands import qa  # noqa: E402
from audiostands.qa.bundle import load_bundle  # noqa: E402
from audiostands.qa.mcp_server import build_server, http_app  # noqa: E402

B = load_bundle()
SIG = B.signals["events"]
PLAYERS = [p for s in ("home", "away") for p in B.meta["teams"][s]["players"]]
URL = "http://localhost:8080/mcp"


def calls_for(p: float, rng: random.Random) -> list[tuple[str, dict]]:
    pl = rng.choice(PLAYERS)
    return [("get_score_and_clock", {}), ("get_ball_position", {}), ("where_is", {"player": pl["last_name"]}),
            ("get_player_stats", {"player": pl["name"]}), ("get_last_events", {"n": rng.randint(1, 5)}),
            ("explain_moment", {"moment_id": rng.choice(list(SIG))}),
            ("what_did_i_miss", {"since": B.clock_str(max(B.t0, p - 90))}), ("set_preferences", {"crowd_mix": 0.3, "haptics": "events"})]


async def over_http(header: str | None, calls: list[tuple[str, dict]]) -> list[dict]:
    srv, app = http_app(B)
    out = []
    async with srv.session_manager.run():
        hc = httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://localhost:8080",
                                headers={"X-AudioStands-Playhead": header} if header is not None else {})
        async with streamable_http_client(URL, http_client=hc) as streams:
            async with ClientSession(streams[0], streams[1]) as s:
                await s.initialize()
                for name, args in calls:
                    r = await s.call_tool(name, args)
                    out.append(r.structured_content if not r.is_error else {"isError": True})
    return out


def test_tools_match_the_relay_schemas_and_take_no_clock():
    async def go():
        async with Client(build_server(B)) as c:
            return (await c.list_tools()).tools
    tools = asyncio.run(go())
    assert sorted(t.name for t in tools) == sorted(s["name"] for s in qa.TOOL_SCHEMAS)
    for t in tools:
        props = set((t.input_schema or {}).get("properties", {}))
        assert not props & {"playhead", "playhead_s", "time", "t", "clock", "ctx"}, (t.name, props)
        assert t.annotations.read_only_hint == (t.name not in {"set_preferences", "adjust_sound"}), t.name


@pytest.mark.parametrize("seed", range(5))
def test_every_tool_clamps_to_the_header_playhead_and_equals_the_relay(seed):
    rng = random.Random(seed)
    for p in [round(rng.uniform(B.t0, B.t1), 2) for _ in range(4)]:
        calls = calls_for(p, rng)
        got = asyncio.run(over_http(str(p), calls))
        for (name, args), r in zip(calls, got):
            assert r == qa.call_tool(name, args, playhead_s=p, bundle=B), (name, p)
            for eid in r.get("evidence_ids", []):
                if eid in SIG:
                    assert SIG[eid]["t"] <= p and SIG[eid]["reveal_t"] <= p, (name, eid, p)


@pytest.mark.parametrize("header, expect", [(None, "start"), ("soon", "start"), ("nan", "start"), ("-5", "start"),
                                            ("99999", "end")])
def test_missing_or_bad_playhead_is_safe(header, expect):
    r = asyncio.run(over_http(header, [("get_score_and_clock", {})]))[0]
    p = B.t0 if expect == "start" else B.t1
    assert r == qa.call_tool("get_score_and_clock", {}, playhead_s=p, bundle=B)


def test_the_model_cannot_set_the_clock_through_arguments():
    # Without a header the answer is as of the cut's start; a sneaked-in playhead argument must not change that.
    r = asyncio.run(over_http(None, [("get_score_and_clock", {"playhead_s": B.t1})]))[0]
    assert r.get("isError") or r == qa.call_tool("get_score_and_clock", {}, playhead_s=B.t0, bundle=B)
