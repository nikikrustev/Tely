"""One fan's live Ask: browser WebSocket <-> one Foundry Voice Live session. OWNER: A (potencialbg).

WHY the GA WebSocket path, not browser WebRTC (docs/DECISIONS.md D17): WebRTC is preview (2026-01-01-preview) and its
event routing is ambiguous (file 40 §2). Through the relay, every event (VAD, transcripts, tool calls, audio) passes one
place, so tool calls, the golden transcripts and the latency log are complete. Audio is PCM16 mono 24 kHz both ways
(the Voice Live default, Learn "How to use the Voice Live API").

The spoiler firewall (file 43 §2): B's tools take no clock argument; the playhead comes from the browser's `ask`
message, is clamped to the cut, and is the only clock call_tool() sees. The model can't move it.
"""
from __future__ import annotations

import base64
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Protocol

# SEAM(A->B): B's Q&A brain (TEAM_SPLIT.md seam 2). Imported, never copied: the clamp B tests is the code that runs live.
from tely.qa import PERSONA, TOOL_SCHEMAS, call_tool
from tely.qa.bundle import Bundle

from .caps import Caps
from .clips import refusal

API_VERSION = "2026-04-10"          # GA WebSocket (file 27 §1; Learn how-to, 8 Oct 2026)
RATE = 24000                        # PCM16 mono, both directions
SILENCE_MS = 500                    # azure_semantic_vad default (file 40 §2)


def model() -> str:
    # D8: the free account has quota for GPT Realtime Mini (Standard tier); the smoke test ran 2.1-mini on 23 Oct.
    return os.environ.get("VOICE_LIVE_MODEL", "gpt-realtime-2.1-mini")


def voice() -> str:
    # Same voice as the pre-rendered commentary (D13), so the answer sounds like the commentator (file 40 §4).
    return os.environ.get("TTS_VOICE", "en-US-Brian:DragonHDLatestNeural")


# Ours, appended to B's PERSONA: how the relay's notes and the tools relate. No facts, no match content.
HOSTING_NOTE = """
# Listening position
Before each question the system notes the match clock the fan is hearing, as [LISTENER AT mm:ss]. The tools already
answer as of that moment; you can't ask them about any other time, and there is nothing later to know.

# Tool speed
The tools answer instantly. Don't say you are going to check or look something up: call the tool, then answer.
Never start with "let me check", "let me see" or "let me look".
"""

# Sent once, after the first answer that said it (the first 31-question run said "I'm an AI voice" in every answer,
# often twice: the pre-tool and post-tool responses each took themselves for the "first answer" in B's PERSONA).
DISCLOSED_NOTE = "[NOTE] You have already told the fan you are an AI voice. Don't say it again."

# Tool-result keys the model never sees: raw pitch coordinates, which it turned into made-up places (D28).
MODEL_HIDDEN = frozenset({"x", "y"})


def add_usage(turn: dict[str, Any], usage: Any) -> None:
    """Sum Voice Live's per-response token counts into the turn (D24: cost per question from real counts). Flat keys:
    total/input/output tokens and their text/audio/cached details, so a golden turn shows what each answer cost."""
    if not isinstance(usage, dict):
        return
    acc = turn.setdefault("usage", {})
    for k, v in usage.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            acc[k] = acc.get(k, 0) + v
        elif isinstance(v, dict):
            for k2, v2 in v.items():
                if isinstance(v2, (int, float)) and not isinstance(v2, bool):
                    key = f"{k}.{k2}"
                    acc[key] = acc.get(key, 0) + v2


def transcription_prompt(b: Bundle) -> str:
    """Player and team names help the transcript of the question (the golden file needs it)."""
    names = sorted({p["last_name"] for p in b.players.values()})
    return f"Football match, {b.team_name('home')} against {b.team_name('away')}. Players: {', '.join(names)}."


def session_update(b: Bundle) -> dict[str, Any]:
    return {"type": "session.update", "session": {
        "instructions": PERSONA + HOSTING_NOTE,
        "modalities": ["text", "audio"],
        "voice": {"type": "azure-standard", "name": voice()},
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "input_audio_sampling_rate": RATE,
        "input_audio_noise_reduction": {"type": "azure_deep_noise_suppression"},
        "input_audio_echo_cancellation": {"type": "server_echo_cancellation"},
        "input_audio_transcription": {"model": "gpt-4o-mini-transcribe", "language": "en",
                                      "prompt": transcription_prompt(b)},
        # WHY: the mic is open only while asking (file 40 §1), so semantic VAD just ends the turn.
        "turn_detection": {"type": "azure_semantic_vad", "silence_duration_ms": SILENCE_MS, "remove_filler_words": True},
        "tools": TOOL_SCHEMAS,                 # SEAM(A->B): B's 8 schemas, sent as-is
        "tool_choice": "auto",
        "max_response_output_tokens": 300,     # file 40 §6 answer-length cap
    }}


class Link(Protocol):
    """The Voice Live connection as the bridge sees it: JSON events in and out."""
    async def send(self, event: dict[str, Any]) -> None: ...
    async def recv(self) -> dict[str, Any]: ...
    async def close(self) -> None: ...


_credential: Any = None


async def connect_voice_live() -> Link:
    """Real connection: managed identity in Container Apps (AZURE_CLIENT_ID), az login locally. No keys anywhere."""
    global _credential
    # Lazy imports: CI and the tests never install Azure packages (TEAM_SPLIT.md rule 3).
    from azure.ai.voicelive.aio import connect
    from azure.identity.aio import DefaultAzureCredential

    if _credential is None:
        _credential = DefaultAzureCredential()   # one per process, so its token cache is reused
    res = os.environ["FOUNDRY_RESOURCE"]
    cm = connect(endpoint=f"https://{res}.services.ai.azure.com/", credential=_credential, model=model(),
                 api_version=API_VERSION)
    conn = await cm.__aenter__()
    return _SdkLink(cm, conn)


class _SdkLink:
    def __init__(self, cm: Any, conn: Any) -> None:
        self._cm, self._conn = cm, conn

    async def send(self, event: dict[str, Any]) -> None:
        await self._conn.send(event)

    async def recv(self) -> dict[str, Any]:
        raw = await self._conn.recv_bytes()
        if not raw:
            raise ConnectionError("Voice Live closed")
        return json.loads(raw)

    async def close(self) -> None:
        try:
            await self._cm.__aexit__(None, None, None)
        except Exception:  # already closed
            pass


def log_line(line: str) -> None:
    """One JSON line to stdout -> Container Apps console logs (relay/golden_from_logs.py reads them). Flushed at once."""
    print(line, flush=True)


SendJson = Callable[[dict[str, Any]], Awaitable[None]]
SendBytes = Callable[[bytes], Awaitable[None]]


class Bridge:
    """State for one browser session. app.py feeds it client messages; pump() feeds it Voice Live events."""

    def __init__(self, link: Link, *, bundle: Bundle, caps: Caps, to_client: SendJson, to_client_audio: SendBytes,
                 connect: Callable[[], Awaitable[Link]] = connect_voice_live, log: Callable[[str], None] | None = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.link, self.bundle, self.caps = link, bundle, caps
        self.to_client, self.to_client_audio, self.connect, self.log, self.clock = (
            to_client, to_client_audio, connect, log or log_line, clock)
        self.opened_at = clock()
        self.playhead = bundle.t0
        self.asked = 0
        self.turn: dict[str, Any] | None = None
        self.listening = False
        self.closed = False
        self._sent_ms = 0.0                       # input audio sent since the last buffer clear (audio_end_ms clock)
        self._marks: list[tuple[float, float]] = []   # (sent_ms at the end of a chunk, wall time it arrived)
        self._pending: list[dict[str, Any]] = []      # function_call_output items, sent after response.done
        self._eos: float | None = None
        self._first_audio: float | None = None
        self._after_tools = False
        self.disclosed = False
        self.levels: dict[str, int] = {}          # the fan's sound levels (0..100) from the last `ask`, for adjust_sound

    async def start(self) -> None:
        await self.link.send(session_update(self.bundle))

    # ---------------------------------------------------------------- from the browser
    async def ask(self, playhead_s: Any, levels: Any = None) -> None:
        """Start one question at the fan's playhead, or send the spoken refusal. `levels` is the page's sound mix on
        the 0..100 scale ({"whistle": 30, ...}); only adjust_sound reads it, so the fan hears the new level."""
        if isinstance(levels, dict):
            self.levels = {k: round(min(100.0, max(0.0, float(v)))) for k, v in levels.items()
                           if isinstance(k, str) and isinstance(v, (int, float)) and not isinstance(v, bool)}
        try:
            p = self.bundle.clamp(float(playhead_s))
        except (TypeError, ValueError):
            p = self.bundle.t0                   # no valid clock: the safest moment (B's mcp_server does the same)
        if (reason := self.caps.question(self.asked)) is not None:
            await self.to_client(refusal(reason))
            return
        if self.clock() - self.opened_at > self.caps.reconnect_after_s:
            await self._reconnect()              # under the 60-min Voice Live session limit (file 40 §2)
        self.asked += 1
        self.playhead = p
        self.turn = {"v": 1, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": model(),
                     "voice": voice(), "api_version": API_VERSION, "playhead_s": round(p, 2),
                     "as_of_clock": self.bundle.clock_str(p), "question": None, "tool_calls": [], "answer": "",
                     "latency_ms": None, "facts_latency_ms": None, "latency_basis": None, "client_latency_ms": None,
                     "outcome": None}
        self._pending, self._eos, self._first_audio, self._after_tools = [], None, None, False
        self._retried = False
        # Measured 23 Oct: the VAD's audio_end_ms counts from the last buffer clear, so our audio clock restarts here.
        self._sent_ms, self._marks = 0.0, []
        await self.link.send({"type": "input_audio_buffer.clear"})
        await self.link.send({"type": "conversation.item.create", "item": {
            "type": "message", "role": "system",
            "content": [{"type": "input_text", "text": f"[LISTENER AT {self.bundle.clock_str(p)}]"}]}})
        self.listening = True
        await self.to_client({"type": "listening", "as_of_clock": self.bundle.clock_str(p)})

    async def audio(self, chunk: bytes) -> None:
        """Mic PCM16 from the browser. Dropped unless a question is open: the gate is enforced here too."""
        if not self.listening or not chunk:
            return
        self._sent_ms += len(chunk) / 2 / RATE * 1000
        self._marks.append((self._sent_ms, time.time()))
        del self._marks[:-500]                   # ~10 s of 20 ms chunks is plenty to find the end of speech
        await self.link.send({"type": "input_audio_buffer.append", "audio": base64.b64encode(chunk).decode()})

    async def commit(self) -> None:
        """The fan talked past the max listen time: end the turn ourselves."""
        if self.listening:
            self.listening = False
            await self.link.send({"type": "input_audio_buffer.commit"})
            await self.link.send({"type": "response.create"})

    async def cancel(self) -> None:
        self.listening = False
        if self.turn is not None:
            self.turn["outcome"] = "cancelled"
            await self.link.send({"type": "response.cancel"})
            await self._finish()

    def metrics(self, client_latency_ms: Any) -> None:
        if self.turn is not None and isinstance(client_latency_ms, (int, float)):
            self.turn["client_latency_ms"] = round(float(client_latency_ms))

    # ---------------------------------------------------------------- from Voice Live
    async def pump(self) -> None:
        while not self.closed:
            link = self.link
            try:
                ev = await link.recv()
            except Exception:
                if link is not self.link:        # we swapped connections on purpose
                    continue
                break
            await self.handle(ev)
        if not self.closed:
            await self.to_client({"type": "error", "reason": "upstream_closed"})

    async def handle(self, ev: dict[str, Any]) -> None:
        t = ev.get("type", "")
        turn = self.turn
        if t == "input_audio_buffer.speech_started":
            await self.to_client({"type": "speech_started"})
        elif t == "input_audio_buffer.speech_stopped":
            self.listening = False
            self.log(json.dumps({"vad_stop": {"audio_end_ms": ev.get("audio_end_ms"), "sent_ms": round(self._sent_ms)}}))
            self._eos, basis = self._end_of_speech(ev.get("audio_end_ms"))
            if turn is not None:
                turn["latency_basis"] = basis
            await self.to_client({"type": "speech_stopped"})
        elif t == "conversation.item.input_audio_transcription.completed" and turn is not None:
            turn["question"] = (ev.get("transcript") or "").strip()
        elif t in ("response.audio.delta", "response.output_audio.delta"):
            if turn is None:
                return                           # a cancelled answer's tail
            now = time.time()
            if self._first_audio is None:
                self._first_audio = now
                if self._eos is not None:
                    turn["latency_ms"] = round((now - self._eos) * 1000)
            # facts_latency_ms: first audio that can carry a tool's answer (after the results went back), so a quick
            # "Let me check" preamble (file 40 §3) doesn't flatter the number. Without tools it equals latency_ms.
            if turn["facts_latency_ms"] is None and self._eos is not None and (self._after_tools or not turn["tool_calls"]):
                turn["facts_latency_ms"] = round((now - self._eos) * 1000)
            await self.to_client_audio(base64.b64decode(ev.get("delta") or ""))
        elif t in ("response.audio_transcript.done", "response.output_audio_transcript.done") and turn is not None:
            said = (ev.get("transcript") or "").strip()
            turn["answer"] = " ".join(s for s in (turn["answer"], said) if s)
            if not self.disclosed and "ai voice" in said.lower():
                self.disclosed = True
                await self.link.send({"type": "conversation.item.create", "item": {
                    "type": "message", "role": "system", "content": [{"type": "input_text", "text": DISCLOSED_NOTE}]}})
        elif t == "response.function_call_arguments.done":
            await self._tool(ev)
        elif t == "response.done":
            if turn is not None:
                add_usage(turn, (ev.get("response") or {}).get("usage"))
            if self._pending:                    # tool results go back only after the response that asked is done
                for item in self._pending:
                    await self.link.send(item)
                self._pending, self._after_tools = [], True
                await self.link.send({"type": "response.create"})
            elif turn is not None:
                resp = ev.get("response") or {}
                status = resp.get("status")
                if self._first_audio is None and status in ("incomplete", "failed") and not self._retried:
                    # Seen live 26 Oct (1 of 4 phone runs): the question was transcribed, then an "incomplete" response
                    # with no audio and no tool call. One fresh response.create answered it; the browser's 8 s timer
                    # still bounds the wait, so a second empty one goes to the presets as before.
                    self._retried = True
                    self.log(json.dumps({"retry_empty_response": {"status": status,
                                                                  "details": resp.get("status_details")}}))
                    await self.link.send({"type": "response.create"})
                    return
                turn["outcome"] = "answered" if self._first_audio is not None else (status or "no_audio")
                await self._finish()
        elif t == "error":
            err = ev.get("error") or {}
            self.log(json.dumps({"voice_live_error": {"code": err.get("code"), "type": err.get("type")}}))
            await self.to_client({"type": "error", "reason": "upstream"})

    async def _tool(self, ev: dict[str, Any]) -> None:
        name = ev.get("name") or ""
        try:
            args = json.loads(ev.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        turn = self.turn if self.turn is not None else {"tool_calls": []}
        if len(turn["tool_calls"]) >= self.caps.tool_calls_per_answer:
            result: dict[str, Any] = {"error": "tool_budget_exceeded", "candidates": []}
        else:
            # SEAM(A->B): call_tool(name, args, playhead_s=..., bundle=...). The playhead is the session's, never the
            # model's: B's tools.call also drops any playhead_s/session_id key the model might invent.
            args = dict(args) if isinstance(args, dict) else {}
            if name == "adjust_sound":           # the page's level, never the model's
                args.pop("current", None)
                if (cur := self.levels.get(str(args.get("sound")))) is not None:
                    args["current"] = cur
            result = call_tool(name, args, playhead_s=self.playhead, bundle=self.bundle)
            prefs = result.get("prefs") or {}
            if name == "adjust_sound" and isinstance(prefs.get("level"), int):
                self.levels[prefs["sound"]] = prefs["level"]   # a second "down by 5" in this answer starts from here
        turn["tool_calls"].append({"name": name, "args": args, "result": result})
        # D28: the model gets the tool's words, not the ball's raw x/y (it read x -53.7, behind the goal line, as "on
        # the sideline near halfway"). The log above keeps them for the evals.
        seen = {k: v for k, v in result.items() if k not in MODEL_HIDDEN}
        self._pending.append({"type": "conversation.item.create", "item": {
            "type": "function_call_output", "call_id": ev.get("call_id"), "output": json.dumps(seen)}})
        # The page pings the ball for get_ball_position and applies set_preferences (file 43 §3).
        await self.to_client({"type": "tool", "name": name, "say": result.get("say"), "prefs": result.get("prefs")})

    def _end_of_speech(self, audio_end_ms: Any) -> tuple[float, str]:
        """Wall time the fan's last word reached the relay: map the VAD's audio_end_ms onto the chunks we sent.
        Falls back to "now" (the VAD event, ~SILENCE_MS late) if it can't be mapped."""
        if isinstance(audio_end_ms, (int, float)):
            for end_ms, wall in self._marks:
                if end_ms >= audio_end_ms:
                    return wall - (end_ms - audio_end_ms) / 1000, "audio_end_ms"
        return time.time(), "vad_event"

    async def _finish(self) -> None:
        turn, self.turn = self.turn, None
        if turn is None:
            return
        self.log(json.dumps({"golden_turn": turn}, ensure_ascii=False))   # for relay/golden_from_logs.py
        await self.to_client({"type": "answer_done", "turn": turn})

    async def _reconnect(self) -> None:
        old = self.link
        self.link = await self.connect()
        await self.start()
        self.opened_at = self.clock()
        await old.close()

    async def close(self) -> None:
        self.closed = True
        await self.link.close()

