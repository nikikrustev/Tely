"""Relay tests. No Azure packages, no keys: Voice Live is a fake Link."""
from __future__ import annotations

import asyncio
import base64
import copy
import json
import random
from pathlib import Path

import pytest

from tely.qa import TOOL_SCHEMAS, call_tool
from tely.qa.bundle import load_bundle
from relay.caps import Caps, RateLimit
from relay.clips import CLIPS, NOTICES, REASON_CLIP
from relay.voicelive import RATE, Bridge, session_update

B = load_bundle()
TOOLS = [t["name"] for t in TOOL_SCHEMAS]


class FakeLink:
    def __init__(self, events=()):
        self.sent: list[dict] = []
        self.inbox: asyncio.Queue = asyncio.Queue()
        for e in events:
            self.inbox.put_nowait(e)
        self.closed = False

    async def send(self, event):
        self.sent.append(event)

    async def recv(self):
        e = await self.inbox.get()
        if e is None:
            raise ConnectionError("closed")
        return e

    async def close(self):
        self.closed = True

    def types(self):
        return [e["type"] for e in self.sent]


def make_bridge(caps: Caps | None = None, link: FakeLink | None = None):
    out, audio, logs = [], [], []

    async def to_client(o):
        out.append(o)

    async def to_audio(b):
        audio.append(b)

    br = Bridge(link or FakeLink(), bundle=B, caps=caps or Caps(), to_client=to_client, to_client_audio=to_audio,
                log=logs.append)
    return br, out, audio, logs


def run(coro):
    return asyncio.run(coro)


def call(name, call_id="c1", **args):
    return {"type": "response.function_call_arguments.done", "name": name, "call_id": call_id,
            "arguments": json.dumps(args)}


# ---------------------------------------------------------------- the playhead is the session's, never the model's
@pytest.mark.parametrize("seed", range(5))
def test_tools_run_at_the_session_playhead_whatever_the_model_sends(seed):
    """Property: across random playheads, every tool the relay runs equals call_tool at the session's playhead, even
    when the model invents a later clock in its arguments (file 43 §2 spoiler firewall)."""
    rng = random.Random(seed)

    async def go():
        br, out, _, _ = make_bridge(Caps(questions_per_session=10**6, daily_questions=10**6))
        for _ in range(40):
            p = rng.uniform(B.t0, B.t1)
            await br.ask(p)
            name = rng.choice(TOOLS)
            args = {"player": "9", "moment_id": B.events[-1]["id"], "since": "00:00", "n": 5}
            args = {k: v for k, v in args.items() if k in _props(name)}
            sneaky = {**args, "playhead_s": B.t1, "session_id": "x"}
            await br.handle(call(name, **sneaky))
            got = br.turn["tool_calls"][-1]["result"]
            assert got == call_tool(name, args, playhead_s=p, bundle=B)
            if "as_of_clock" in got:
                assert got["as_of_clock"] == B.clock_str(p)
            await br.cancel()
    run(go())


def _props(name):
    return next(t for t in TOOL_SCHEMAS if t["name"] == name)["parameters"].get("properties", {})


def test_set_preferences_never_touches_match_state():
    async def go():
        before = (copy.deepcopy(B.events), copy.deepcopy(B.signals), copy.deepcopy(B.meta))
        br, out, _, _ = make_bridge()
        p = (B.t0 + B.t1) / 2
        await br.ask(p)
        score = call_tool("get_score_and_clock", {}, playhead_s=p, bundle=B)
        await br.handle(call("set_preferences", verbosity="calm", crowd_mix=0.2, haptics="off"))
        assert br.playhead == p
        assert call_tool("get_score_and_clock", {}, playhead_s=p, bundle=B) == score
        assert (B.events, B.signals, B.meta) == before
        tool_msg = [o for o in out if o["type"] == "tool"][-1]
        assert tool_msg["prefs"] == {"crowd_mix": 0.2, "haptics": "off"}   # "verbosity" is not a setting: dropped (D30)
        assert "key moments only, or the full radio" in tool_msg["say"]
    run(go())


def test_adjust_sound_starts_from_the_pages_level_not_the_models():
    async def go():
        br, out, _, _ = make_bridge()
        await br.ask((B.t0 + B.t1) / 2, {"whistle": 30, "crowd": 50.4, "bad": "x"})
        assert br.levels == {"whistle": 30, "crowd": 50}
        await br.handle(call("adjust_sound", sound="whistle", change=-5, current=99))   # the model's "current" is ignored
        tool_msg = [o for o in out if o["type"] == "tool"][-1]
        assert tool_msg["prefs"] == {"sound": "whistle", "level": 25}
        assert tool_msg["say"] == "The whistle is now 25 out of 100."
        await br.handle(call("adjust_sound", sound="whistle", change=-5))                # same answer: from 25
        assert [o for o in out if o["type"] == "tool"][-1]["prefs"] == {"sound": "whistle", "level": 20}
    run(go())


def test_language_from_the_page_and_from_set_language_switch_voice_and_instructions():
    async def go():
        link = FakeLink()
        br, out, _, _ = make_bridge(link=link)
        await br.ask((B.t0 + B.t1) / 2, None, "bg")
        upd = [e for e in link.sent if e.get("type") == "session.update"][-1]["session"]
        assert br.lang == "bg" and upd["voice"]["name"] == "en-US-BrianMultilingualNeural"
        assert "Speak only Bulgarian" in upd["instructions"] and upd["input_audio_transcription"]["language"] == "bg"
        n = len([e for e in link.sent if e.get("type") == "session.update"])
        await br.ask((B.t0 + B.t1) / 2, None, "bg")                      # same language: no update
        assert len([e for e in link.sent if e.get("type") == "session.update"]) == n
        await br.handle(call("set_language", language="de"))
        assert [o for o in out if o["type"] == "tool"][-1]["prefs"] == {"language": "de"}
        assert br.lang == "de" and br._pending[-1]["type"] == "session.update"   # goes with the tool result
        assert "Speak only German" in br._pending[-1]["session"]["instructions"]
        await br.handle(call("set_language", language="en"))
        assert br._pending[-1]["session"]["voice"]["name"] == "en-US-Brian:DragonHDLatestNeural"
        assert "# Language" not in br._pending[-1]["session"]["instructions"]
    run(go())


# ---------------------------------------------------------------- caps return a spoken refusal
def test_session_cap_is_a_spoken_refusal():
    async def go():
        br, out, _, _ = make_bridge(Caps(questions_per_session=2))
        for _ in range(3):
            await br.ask(B.t0)
        refusals = [o for o in out if o["type"] == "refusal"]
        assert len(refusals) == 1
        r = refusals[0]
        assert r["reason"] == "session_cap" and r["clip"] in CLIPS and r["say"] == CLIPS[r["clip"]]
        assert "preset" in r["say"]
    run(go())


def test_daily_cap_and_demo_mode(monkeypatch):
    c = Caps(daily_questions=1)
    assert c.question(0) is None
    assert c.question(0) is None                          # asking counts nothing...
    c.count_question()
    assert c.question(0) == "daily_cap"                   # ...a question Voice Live heard does
    monkeypatch.setenv("DEMO_MODE", "off")
    assert Caps().question(0) == "demo_off"
    assert Caps().open_session("1.2.3.4") == "demo_off"


def test_per_ip_limits():
    t = [1000.0]
    c = Caps(sessions_per_ip=3, open_per_ip=2, clock=lambda: t[0])
    assert c.open_session("ip") is None and c.open_session("ip") is None
    assert c.open_session("ip") == "busy"                 # two already open
    c.close_session("ip")
    assert c.open_session("ip") is None                   # third in the window
    c.close_session("ip")
    assert c.open_session("ip") == "rate_limit"           # window full
    t[0] += 601
    assert c.open_session("ip") is None                   # the window moved on
    assert c.open_session("other") is None


def test_per_ip_daily_question_cap(monkeypatch):
    monkeypatch.setenv("DAILY_QUESTION_CAP_PER_IP", "2")
    c = Caps()
    assert c.daily_questions_per_ip == 2
    c.count_question("a")
    c.count_question("a")
    assert c.question(0, "a") == "daily_cap" and c.open_session("a") == "daily_cap"
    assert c.question(0, "b") is None                     # another fan is not affected
    assert c._today == 2


def test_the_per_ip_counters_are_pruned():
    t = [1000.0]
    c = Caps(prune_above=3, clock=lambda: t[0])
    for i in range(3):
        assert c.open_session(f"ip{i}") is None
        c.close_session(f"ip{i}")
    assert not c._open                                    # closed sessions leave no zero entries
    assert c.open_session("held") is None                 # still open: kept however old
    t[0] += 601
    assert c.open_session("new") is None
    assert set(c._opened) == {"held", "new"}


def test_rate_limit_window_and_pruning():
    t = [0.0]
    r = RateLimit(per_ip=2, window_s=60, prune_above=3, clock=lambda: t[0])
    assert r.allow("a") and r.allow("a") and not r.allow("a")
    for ip in ("b", "c"):
        assert r.allow(ip)
    t[0] += 61
    assert r.allow("a")                                   # the window moved on
    assert r.allow("d") and set(r._hits) == {"a", "d"}    # b and c were forgotten


def test_every_refusal_reason_has_a_clip():
    for reason, clip in REASON_CLIP.items():
        assert clip in CLIPS, reason
    for text in CLIPS.values():
        assert "preset" in text                           # every refusal points the fan at the presets


def test_the_waking_line_is_the_one_the_page_says():
    # web/src/voice/live-ask.ts falls back to the browser voice with the same words until the clip is rendered.
    page = (Path(__file__).resolve().parents[2] / "web" / "src" / "voice" / "live-ask.ts").read_text(encoding="utf-8")
    for cid, text in NOTICES.items():
        assert f"clip: '{cid}', say: '{text}'" in page


# ---------------------------------------------------------------- the Voice Live turn
def test_a_turn_end_to_end_makes_a_golden_record():
    async def go():
        link = FakeLink()
        br, out, audio, logs = make_bridge(link=link)
        await br.start()
        assert link.sent[0]["type"] == "session.update"
        p = B.t0 + 60
        await br.ask(p)
        assert link.types()[-2:] == ["input_audio_buffer.clear", "conversation.item.create"]
        assert out[-1] == {"type": "listening", "as_of_clock": B.clock_str(p)}
        chunk = b"\x00\x01" * (RATE // 50)                # 20 ms
        for _ in range(50):
            await br.audio(chunk)
        assert link.types().count("input_audio_buffer.append") == 50
        await br.handle({"type": "input_audio_buffer.speech_started"})
        await br.handle({"type": "input_audio_buffer.speech_stopped", "audio_end_ms": 900})
        await br.audio(chunk)                             # the gate closed at end of speech
        assert link.types().count("input_audio_buffer.append") == 50
        await br.handle({"type": "conversation.item.input_audio_transcription.completed",
                         "transcript": " Where's the ball? "})
        await br.handle(call("get_ball_position", call_id="c9"))
        assert "function_call_output" not in json.dumps(link.sent)   # not before response.done
        await br.handle({"type": "response.done", "response": {"status": "completed"}})
        assert link.types()[-2:] == ["conversation.item.create", "response.create"]
        seen = json.loads(link.sent[-2]["item"]["output"])
        assert seen["say"] and not {"x", "y"} & seen.keys()      # D28: the model never gets the raw coordinates
        await br.handle({"type": "response.audio.delta", "delta": base64.b64encode(b"\x01\x02").decode()})
        br.metrics(1234.4)
        await br.handle({"type": "response.audio_transcript.done", "transcript": "Navy have it."})
        await br.handle({"type": "response.done", "response": {"status": "completed"}})
        assert audio == [b"\x01\x02"]
        done = [o for o in out if o["type"] == "answer_done"]
        assert len(done) == 1
        rec = done[0]["turn"]
        assert rec["question"] == "Where's the ball?" and rec["answer"] == "Navy have it."
        assert rec["tool_calls"][0]["name"] == "get_ball_position"
        assert {"x", "y"} <= rec["tool_calls"][0]["result"].keys()     # ...but the log keeps them for the evals
        assert rec["outcome"] == "answered" and rec["latency_basis"] == "audio_end_ms"
        assert isinstance(rec["latency_ms"], int) and rec["latency_ms"] >= 0
        assert isinstance(rec["facts_latency_ms"], int) and rec["facts_latency_ms"] >= rec["latency_ms"]
        assert rec["client_latency_ms"] == 1234
        assert any(o == {"type": "tool", "name": "get_ball_position", "say": rec["tool_calls"][0]["result"]["say"],
                         "prefs": None} for o in out)
        logged = json.loads(logs[-1])["golden_turn"]
        assert logged == rec
        assert not set(json.dumps(rec).lower().split('"')) & {"api-key", "authorization", "token"}
    run(go())


def test_latency_restarts_with_each_question():
    """audio_end_ms counts from the last input_audio_buffer.clear (measured on Voice Live, 23 Oct 2026)."""
    async def go():
        br, out, _, _ = make_bridge()
        chunk = bytes(2 * RATE // 50)                    # 20 ms of silence
        for q in range(2):
            await br.ask(B.t0 + 10 * q)
            for _ in range(100):                          # 2 s of audio each time
                await br.audio(chunk)
            await br.handle({"type": "input_audio_buffer.speech_stopped", "audio_end_ms": 1500})
            assert br.turn["latency_basis"] == "audio_end_ms"
            await br.handle({"type": "response.audio.delta", "delta": "AAA="})
            assert 0 <= br.turn["latency_ms"] < 2000        # mapped inside this question's audio, not the last one's
            await br.handle({"type": "response.done", "response": {"status": "completed"}})
    run(go())


def test_an_empty_incomplete_response_is_retried_once():
    """26 Oct phone run: Voice Live returned an "incomplete" response with no audio after a clear question."""
    async def go():
        link = FakeLink()
        br, out, _, logs = make_bridge(link=link)
        await br.ask(B.t0 + 30)
        await br.handle({"type": "input_audio_buffer.speech_stopped", "audio_end_ms": 900})
        await br.handle({"type": "response.done", "response": {"status": "incomplete"}})
        assert link.types()[-1] == "response.create"         # one retry, no answer_done yet
        assert not [o for o in out if o["type"] == "answer_done"]
        assert "retry_empty_response" in logs[-1]
        await br.handle({"type": "response.done", "response": {"status": "incomplete"}})
        done = [o for o in out if o["type"] == "answer_done"]
        assert len(done) == 1 and done[0]["turn"]["outcome"] == "incomplete"   # never a second retry
        await br.ask(B.t0 + 40)                              # the next question may retry again
        await br.handle({"type": "response.done", "response": {"status": "incomplete"}})
        assert link.types()[-1] == "response.create"
    run(go())


def test_token_usage_is_summed_into_the_turn():
    async def go():
        br, out, _, _ = make_bridge()
        await br.ask(B.t0 + 30)
        await br.handle({"type": "response.audio.delta", "delta": "AAA="})
        use = {"total_tokens": 100, "input_tokens": 80, "output_tokens": 20,
               "output_token_details": {"audio_tokens": 15, "text_tokens": 5}, "note": "x"}
        await br.handle({"type": "response.done", "response": {"status": "completed", "usage": use}})
        rec = [o for o in out if o["type"] == "answer_done"][0]["turn"]
        assert rec["usage"] == {"total_tokens": 100, "input_tokens": 80, "output_tokens": 20,
                                "output_token_details.audio_tokens": 15, "output_token_details.text_tokens": 5}
    run(go())


def test_ai_voice_disclosure_is_said_once():
    async def go():
        link = FakeLink()
        br, _, _, _ = make_bridge(link=link)
        await br.ask(B.t0)
        for _ in range(2):
            await br.handle({"type": "response.audio_transcript.done", "transcript": "I'm an AI voice. Nil nil."})
        notes = [e for e in link.sent if "already told the fan" in json.dumps(e)]
        assert len(notes) == 1 and notes[0]["item"]["role"] == "system"
    run(go())


def test_tool_budget_per_answer():
    async def go():
        br, _, _, _ = make_bridge(Caps(tool_calls_per_answer=2))
        await br.ask(B.t0 + 30)
        for i in range(3):
            await br.handle(call("get_score_and_clock", call_id=f"c{i}"))
        assert br.turn["tool_calls"][-1]["result"]["error"] == "tool_budget_exceeded"
    run(go())


def test_a_question_counts_only_once_voice_live_heard_it():
    """An `ask` with no audio costs nothing upstream, so it must not use up the daily caps (review item 15)."""
    async def go():
        caps = Caps(questions_per_session=10**6)
        br, _, _, _ = make_bridge(caps)
        br.ip = "203.0.113.9"
        for _ in range(300):
            await br.ask(B.t0)
        assert caps._today == 0
        await br.handle({"type": "conversation.item.input_audio_transcription.completed", "transcript": "Score?"})
        await br.handle({"type": "response.created"})
        await br.handle({"type": "response.audio.delta", "delta": "AAA="})
        assert caps._today == 1 and caps._ip_today["203.0.113.9"] == 1   # once per question
        await br.ask(B.t0)
        await br.handle({"type": "response.created"})                    # a response with no transcript also counts
        assert caps._today == 2
    run(go())


def test_the_relay_ends_a_long_turn_itself_from_the_first_audio():
    """Server-side max_listen_s: timed from the first mic chunk (the browser may sit in a mic permission prompt
    after `listening`), restarted at speech_started, with a grace after the browser's own commit."""
    async def go():
        t = [0.0]
        link = FakeLink()
        out = []

        async def sink(o):
            out.append(o)

        caps = Caps()
        br = Bridge(link, bundle=B, caps=caps, to_client=sink, to_client_audio=sink, log=lambda s: None,
                    clock=lambda: t[0])
        chunk = bytes(2 * RATE // 50)                    # 20 ms
        await br.ask(B.t0)
        t[0] = 30.0                                      # a slow permission prompt: no commit for that
        await br.audio(chunk)
        t[0] = 31.0
        await br.handle({"type": "input_audio_buffer.speech_started"})
        t[0] = 31.0 + caps.max_listen_s + caps.listen_grace_s - 0.5
        await br.audio(chunk)
        assert "input_audio_buffer.commit" not in link.types()
        t[0] += 1.0
        await br.audio(chunk)
        assert link.types()[-2:] == ["input_audio_buffer.commit", "response.create"] and not br.listening
        # Faster than real time: 16 s of audio at one instant is past the limit too.
        await br.ask(B.t0)
        for _ in range(16 * 50):
            await br.audio(chunk)
        assert link.types().count("input_audio_buffer.commit") == 2
    run(go())


def test_audio_per_session_is_capped():
    async def go():
        link = FakeLink()
        br, out, _, _ = make_bridge(Caps(audio_bytes_per_session=2 * 960), link)
        await br.ask(B.t0)
        for _ in range(3):
            await br.audio(b"\x00\x00" * 480)
        assert link.types().count("input_audio_buffer.append") == 2
        assert link.types()[-2:] == ["input_audio_buffer.commit", "response.create"]
        await br.ask(B.t0)
        assert out[-1]["type"] == "refusal" and out[-1]["reason"] == "session_cap"
    run(go())


def test_after_the_tool_budget_the_next_response_may_only_speak():
    async def go():
        link = FakeLink()
        br, _, _, _ = make_bridge(Caps(tool_calls_per_answer=1), link)
        await br.ask(B.t0 + 30)
        await br.handle(call("get_score_and_clock"))
        await br.handle({"type": "response.done", "response": {"status": "completed"}})
        assert link.sent[-1] == {"type": "response.create", "response": {"tool_choice": "none"}}
        br2, _, _, _ = make_bridge(Caps(tool_calls_per_answer=2), link2 := FakeLink())
        await br2.ask(B.t0 + 30)
        await br2.handle(call("get_score_and_clock"))
        await br2.handle({"type": "response.done", "response": {"status": "completed"}})
        assert link2.sent[-1] == {"type": "response.create"}          # budget left: tools still allowed
    run(go())


def test_mic_audio_is_dropped_without_a_question():
    async def go():
        link = FakeLink()
        br, _, _, _ = make_bridge(link=link)
        await br.audio(b"\x00\x00" * 480)
        assert link.sent == []
    run(go())


def test_reconnects_before_the_60_minute_limit():
    async def go():
        t = [0.0]
        new = FakeLink()

        async def connect():
            return new

        old = FakeLink()
        out = []

        async def sink(o):
            out.append(o)

        br = Bridge(old, bundle=B, caps=Caps(), to_client=sink, to_client_audio=sink, connect=connect,
                    log=lambda s: None, clock=lambda: t[0])
        await br.ask(B.t0)
        t[0] = 56 * 60
        await br.ask(B.t0 + 10)
        assert old.closed and br.link is new
        assert new.sent[0]["type"] == "session.update"
    run(go())


def test_session_update_uses_b_persona_and_tools():
    s = session_update(B)["session"]
    assert s["tools"] == TOOL_SCHEMAS
    assert s["instructions"].startswith("# Role")
    assert s["voice"]["name"].endswith("DragonHDLatestNeural")
    assert all(name not in json.dumps(s["tools"]) for name in ("playhead", "clock_s"))   # the model has no clock knob
