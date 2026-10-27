"""The relay over HTTP and WebSocket, with a fake Voice Live. OWNER: A (potencialbg). No Azure packages, no keys."""
from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from tely.qa.bundle import load_bundle
from relay.app import create_app
from relay.caps import Caps

B = load_bundle()


class ScriptedLink:
    """Answers every question with one get_ball_position call and a short spoken answer."""

    def __init__(self):
        self.q: asyncio.Queue = asyncio.Queue()
        self.sent: list[dict] = []

    async def send(self, e):
        self.sent.append(e)
        t = e["type"]
        if t == "input_audio_buffer.append" and sum(x["type"] == t for x in self.sent) == 3:
            for ev in ({"type": "input_audio_buffer.speech_started"},
                       {"type": "input_audio_buffer.speech_stopped", "audio_end_ms": 40},
                       {"type": "conversation.item.input_audio_transcription.completed", "transcript": "Ball?"},
                       {"type": "response.function_call_arguments.done", "name": "get_ball_position",
                        "call_id": "c1", "arguments": "{}"},
                       {"type": "response.done", "response": {"status": "completed"}}):
                self.q.put_nowait(ev)
        if t == "response.create":
            for ev in ({"type": "response.audio.delta", "delta": "AAA="},
                       {"type": "response.audio_transcript.done", "transcript": "Here."},
                       {"type": "response.done", "response": {"status": "completed"}}):
                self.q.put_nowait(ev)

    async def recv(self):
        return await self.q.get()

    async def close(self):
        pass


def client(connect=None, caps=None, mount_mcp=False):
    async def fail():
        raise ConnectionError("no voice live in tests")
    return TestClient(create_app(bundle=B, caps=caps or Caps(), connect=connect or fail, mount_mcp=mount_mcp))


def test_health():
    with client() as c:
        assert c.get("/health").json() == {"ok": True, "mode": "live"}


def test_demo_mode_off_refuses_out_loud(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "off")
    with client() as c, c.websocket_connect("/voice") as ws:
        m = ws.receive_json()
        assert m["type"] == "refusal" and m["reason"] == "demo_off" and m["say"]


def test_no_voice_live_says_unavailable():
    with client() as c, c.websocket_connect("/voice") as ws:
        m = ws.receive_json()
        assert m["type"] == "refusal" and m["clip"] == "live_unavailable"


def test_foreign_origin_is_closed():
    with client() as c:
        with pytest.raises(Exception):
            with c.websocket_connect("/voice", headers={"origin": "https://evil.example"}) as ws:
                ws.receive_json()


def test_one_live_question_over_the_websocket():
    link = ScriptedLink()

    async def connect():
        return link

    with client(connect) as c, c.websocket_connect("/voice") as ws:
        assert ws.receive_json() == {"type": "ready"}
        ws.send_text(json.dumps({"type": "ask", "playhead_s": B.t0 + 45}))
        assert ws.receive_json()["type"] == "listening"
        for _ in range(3):
            ws.send_bytes(b"\x00\x00" * 480)
        seen, audio = [], []
        while not seen or seen[-1]["type"] != "answer_done":
            msg = ws.receive()
            if msg.get("bytes") is not None:
                audio.append(msg["bytes"])
            else:
                seen.append(json.loads(msg["text"]))
        kinds = [m["type"] for m in seen]
        assert kinds[:2] == ["speech_started", "speech_stopped"] and "tool" in kinds
        assert audio == [b"\x00\x00"]
        turn = seen[-1]["turn"]
        assert turn["question"] == "Ball?" and turn["answer"] == "Here."
        assert turn["tool_calls"][0]["result"]["as_of_clock"] == B.clock_str(B.t0 + 45)
    assert link.sent[0]["type"] == "session.update"


def test_session_cap_over_the_websocket():
    link = ScriptedLink()

    async def connect():
        return link

    with client(connect, Caps(questions_per_session=0)) as c, c.websocket_connect("/voice") as ws:
        ws.receive_json()
        ws.send_text(json.dumps({"type": "ask", "playhead_s": B.t0}))
        m = ws.receive_json()
        assert m["type"] == "refusal" and m["reason"] == "session_cap"


def test_b_mcp_server_is_mounted_at_mcp(monkeypatch):
    pytest.importorskip("mcp")
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "testserver")     # infra sets our public host name the same way
    hdr = {"accept": "application/json, text/event-stream", "content-type": "application/json",
           "x-tely-playhead": str(B.t0 + 45)}
    with client(mount_mcp=True) as c:
        init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                           "clientInfo": {"name": "test", "version": "0"}}}
        assert c.post("/mcp", json=init, headers=hdr).status_code == 200
        tools = c.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, headers=hdr).json()
        assert len(tools["result"]["tools"]) == 10
        r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                 "params": {"name": "get_score_and_clock", "arguments": {}}}, headers=hdr).json()
        assert B.clock_str(B.t0 + 45) in json.dumps(r)
        assert c.get("/health").status_code == 200        # our routes still win over the mount


def test_mcp_rejects_unknown_host_names():
    pytest.importorskip("mcp")
    with client(mount_mcp=True) as c:                     # default: localhost only (B's DNS-rebinding protection)
        r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                   headers={"accept": "application/json, text/event-stream"})
        assert r.status_code == 421
