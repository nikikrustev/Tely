# 40 — Talking to the commentator mid-match: voice Q&A grounded in live match state

_Accessed/compiled: 20 Oct 2026 · Priority area: Personalise + Render (two-way audio) for Tely; Explain (answers come from tools, not model memory)_

## TL;DR

- **Use a toggle "Ask" button, not a wake word and not an always-open mic.** One large native button, which a VoiceOver or TalkBack user activates with a plain double-tap. The mic is gated: it is open only between the two presses. Hold-to-talk is awkward under VoiceOver, because a hold needs the pass-through gesture ("double-tap and hold … until you hear three rising tones"). Gating the mic also deals with crowd audio and echo: we duck our own crowd bed while the fan speaks, so the mic mostly hears the fan.
- **Voice Live over WebRTC fits Tely. The tool calls run on our server, not in the browser.** The docs describe three channels:
  - audio over RTP;
  - a browser data channel `voice-live-events` that carries VAD and response events;
  - a WebSocket control channel, "typically initiated by your server", which carries `session.update` and **all function-call events**.

  So a small relay holds the Entra token, swaps SDP for the browser, and answers tool calls straight from the stats engine. Limits: sessions last **≤ 60 minutes**, and a resource allows 100 new connections per minute and 120,000 tokens per minute. A 90-minute match therefore needs lazy, reconnectable sessions.
- **Six read-only tools ground every answer:** `get_score_and_clock`, `get_ball_position`, `where_is`, `get_player_stats`, `get_last_events`, `explain_moment`. They are the same functions as the file 18 Stats MCP server. They return spoken-ready text plus evidence ids, and they are **clamped to the listener's delayed clock**. That clamp matters: the look-ahead that lets the commentator build tension must never leak into an answer as a spoiler.
- **One persona across commentary and answers comes almost free.** Voice Live speaks with the same Azure TTS voices we use to pre-render commentary (HD voices work in every Voice Live region), so the timbre is identical. We share one persona prompt block, and the relay feeds every line that has aired into the conversation as labelled system items.
- **Bulgarian works, but use the toggle rather than open-mic.** `gpt-realtime` lists Bulgarian and so does `mai-transcribe-2`. `azure-speech` (which pairs only with non-realtime models) needs `language: "bg-BG"` set explicitly, because the auto-detect list excludes Bulgarian. Semantic-VAD filler-word removal does not cover Bulgarian, so open-mic barge-in would false-trigger more often. Answer with `bg-BG-BorislavNeural`, which has no styles, only prosody (file 27).

> **Correction (from [43](43-tely-architecture.md)):** Microsoft Learn lists only **en-US** DragonHD voices, so `en-GB-Ollie`/`en-GB-…:DragonHDLatestNeural` HD names used below should be replaced by an en-US DragonHD (or DragonHD Omni) voice. DragonHD supports `<break>` but not `prosody`/`express-as`; Omni supports `express-as` but not `<break>`. HD voices are real-time only (no batch pre-render).

## Findings

### 1. Interaction model: how the fan asks

| Model | For blind users | In crowd noise | Verdict |
|---|---|---|---|
| **Toggle "Ask" button** (double-tap start, auto-stop on end of speech, double-tap again to send early) | Works with a standard VoiceOver/TalkBack activation. State is announced with `aria-pressed`. | The mic is closed except while asking, and we duck our crowd bed during the ask. | **Recommended** |
| Hold-to-talk | VoiceOver needs the pass-through "double-tap and hold until three rising tones" gesture (Apple VoiceOver gestures). Awkward. | Good | Desktop keyboard only |
| Wake word ("Hey coach") | Hands-free, but there is no wake-word engine in Voice Live (I found none in the docs), so we would have to run one in the browser. | Crowd chants cause false triggers (unverified) | Skip |
| Always-on mic with semantic VAD + barge-in | No button to find | `remove_filler_words` helps, but **only for EN/ES/FR/IT/DE/JA/PT/ZH/KO/HI**. The server AEC assumes we play the model's audio immediately, yet we mix crowd and commentary locally. | Optional "open mic" mode for English with headphones only |

**Screen-reader specifics.**
- **Both readers duck other audio.** TalkBack's audio ducking "lowers the volume level of media and other audio so TalkBack's spoken feedback is easy to understand" and is "on by default". Every `aria-live` announcement therefore dips our commentary.
  - In Tely mode, mute the per-cue live regions from file 32. The fan already *hears* the cues. Keep live regions only for state changes ("Listening", "Answer stopped").
- **Give a magic tap a job.** VoiceOver's two-finger double tap is "Start or stop the current action (for example, play or pause music or a video…)". We cannot verify that it reaches a web page; it probably arrives as a media play/pause.
  - Register Media Session `play`/`pause` handlers that toggle Ask. MDN says these fire on "built-in physical or onscreen media controls", which covers a headset button.
  - Browser support is "limited availability", so treat this as a bonus and keep the button primary.
- **Keep the screen reader's voice out of the transcript.** The reader's own voice ("Ask, toggle button, pressed") comes from the operating system. The browser's echo canceller may not remove it (unverified). So play our "listening" earcon and open the mic about 250 ms after the press. Keep the button's accessible name to one word.
- **Let the fan stop and control the answer.** The ASSETS 2018 interview study with 14 blind voice-assistant users found problems "relating to the input, responses … and control of information presented". Give the fan:
  - an instant **Stop** (pressing Ask while an answer plays cancels it);
  - a **speech-rate setting** (Voice Live voice `rate` 0.5–1.5);
  - a **"repeat"** request.

**Pause, duck, resume, catch up.** These are our design rules.
- **States:** `LIVE → LISTENING → THINKING → ANSWERING → RESUMING → LIVE`.
- **On press:** pause the commentary queue (don't duck it, because two voices at once are unintelligible), duck the crowd to about 15%, play the earcon, open the mic.
- **While paused:** low-priority cues expire by their `ttl_ms`, as in the file 24 scheduler.
- **After `response.done`:** wait until the remote audio has been silent for about 600 ms. `response.done` fires when *generation* ends, which is before playback ends. OpenAI's WebRTC `output_audio_buffer.stopped` event would be cleaner, but the Voice Live data-channel list doesn't include it.
- **Then resume** with one templated, verified line, "…back to the action: while we talked, Rovers won a corner and Vale made a change", built from the events between `qa_started_at` and now (code below).
- **If a goal-priority cue arrives mid-answer:** send `response.cancel` and play the goal. Afterwards, offer "Want the rest of that answer?" with a `response.create` that carries instruction overrides.
- **Use the look-ahead.** Because we run on a delay, the server knows when a big moment is under about 8 s away (threshold ours). If the fan presses Ask then, the commentator says "Hold that thought, watch this!" and defers the question. It never says *what* is coming.

### 2. Voice Live session: what the docs pin down

- **WebRTC endpoint:** `wss://<res>.services.ai.azure.com/voice-live/realtime/calls?api-version=2026-01-01-preview&model=…`. The sample uses a *preview* API version (the GA WebSocket path uses `2026-04-10`), so treat WebRTC as preview.
- **Signalling:**
  - The client sends `rtc.call.sdp.create {sdp_offer, session}` and receives `rtc.call.sdp.created {sdp_answer}`. Errors come back as `rtc.call.error`.
  - The full sample creates the data channel **before** `createOffer`, so that the channel appears in the SDP.
- **Event routing:**
  - **Control WebSocket:** `session.*`, `error`, `response.function_call_arguments.delta/done`.
  - **Data channel:** `input_audio_buffer.speech_started/stopped`, `response.created/done`, transcripts.
  - **Ambiguous:** the page lists `response.output_item.*` under control but also says those items are "routed to the data channel instead". Our relay handles both cases.
- **Auth:**
  - Entra bearer token with scope `https://ai.azure.com/.default`, plus the *Cognitive Services User* and *Foundry User* roles.
  - The browser cannot set the header, and the only browser-side option is an `api-key` query string. Hence the relay: no key ever ships to the page.
- **Turn detection:**
  - `server_vad` is the default. `azure_semantic_vad` and `azure_semantic_vad_multilingual` work with all models.
  - `silence_duration_ms` defaults to **500**. `interrupt_response` defaults to true, but only on the Azure semantic types.
  - `create_response` can be switched off.
  - True push-to-talk in the Realtime API means `turn_detection: null` → `input_audio_buffer.commit` → `response.create`, and "WebRTC/SIP must clear explicitly" with `input_audio_buffer.clear`. Voice Live support for the `null` form is **unverified**.
  - So the code below uses **gated VAD**: the mic track is enabled only while asking, and VAD ends the turn.
- **Response control** (OpenAI reference, which Voice Live "mostly matches"):
  - `response.create.response.max_output_tokens` (1–4096) is our per-answer length cap.
  - `instructions` overrides the session instructions for one response.
  - `conversation: "none"` gives an out-of-band response.
  - `output_audio_buffer.clear` is "WebRTC/SIP Only … cut off the current audio response", sent after `response.cancel`.
- **Context injection:** `conversation.item.create` accepts `system` messages (content `input_text`), so aired commentary goes in that way.
- **Limits** (Speech quotas page, S0):
  - 100 new connections per minute;
  - **≤ 60 minutes per session**;
  - ≤ 120,000 tokens per minute, where TPM = NCPM × 4,000.

  The F0 tier is "Not applicable", so Voice Live **needs S0**.

### 3. Grounding: tools, MCP design, latency

Each tool is a thin wrapper over the file 18 stats engine. The same Python function is registered on the `MCPServer` (so it earns the "MCP integration" credit) and on a REST route that the relay calls.

| Tool | Args | Returns (`say` + data + `evidence_ids`) |
|---|---|---|
| `get_score_and_clock` | none | "Rovers 1, Vale 0, 63rd minute" |
| `get_ball_position` | none | Zone words ("right wing, about 25 m from Vale's goal") plus x/y |
| `where_is` | `player` (name or shirt number) | The player's zone and distance to the ball |
| `get_player_stats` | `player`, `metrics[]` | Distance, top speed, passes, shots up to now |
| `get_last_events` | `n` ≤ 5 | Newest first, one short line each |
| `explain_moment` | `moment_id` | **Cached** verified explanation from the Explain stage (file 22). No new LLM text. |

**Design rules:**
- **MCP spec:**
  - servers "MUST validate all tool inputs … rate limit tool invocations";
  - input errors go back as `isError: true` with "actionable feedback";
  - parameterless tools use `{"type":"object","additionalProperties":false}`.
- **Anthropic's tool-writing guide:**
  - return names, not ids;
  - offer concise output (it cut tokens to about a third);
  - use unambiguous parameter names;
  - consolidate tools rather than mirror every endpoint.
- **Name matching:** names are fuzzy-matched. If the match is ambiguous, the tool returns candidates and the model asks. Google's guide says to use explicit confirmation only when misunderstanding is costly. A stat lookup is cheap, so confirm implicitly: "Kovač, the number 9, has run 8.2 km".
- **Prompting (OpenAI realtime prompting guide):**
  - "Do not invent, assume, simulate, or rename tools";
  - "Direct answers: Use 1-2 short sentences";
  - give a one-line preamble ("I'll check that now") only before slow tools;
  - set reasoning effort to "low".
- **Brevity check:** Alexa's "one-breath test" is a good gate for answer length.

**Latency budget.** Only the sourced figures are hard numbers. Everything else is ours to measure.

| Step | Figure | Source |
|---|---|---|
| Human gap between turns | Mean **+208 ms** across 10 languages | Stivers et al. 2009 (PNAS) |
| End of speech → turn ends (VAD) | `silence_duration_ms` default **500 ms**, tunable | Voice Live how-to |
| Model first audio | **Not published.** Read `gen_ai.voice.first_token_latency_ms` from SDK telemetry | File 27 |
| Relay → tool API → engine | Ours to measure. Keep in the same region as Voice Live and the engine. | (ours) |
| Spoken preamble masking a slow tool | One short sentence | OpenAI prompting guide |

**Implication:** we cannot match +208 ms. An earcon when the fan stops talking, plus the preamble, makes the wait feel intentional. Log press → first audio per answer and show the p50/p95 in the demo.

### 4. Persona consistency and shared context

- **Same voice:**
  - Commentary is pre-rendered with Azure TTS (SSML, file 27).
  - Voice Live answers use `voice: {type: "azure-standard", name: "en-GB-Ollie:DragonHDLatestNeural"}`. Voice Live "routes HD voice synthesis to a supported speech region", so the HD voice works wherever our resource sits.
  - In Bulgarian, both use `bg-BG-BorislavNeural`.
  - The raw `gpt-realtime` native voices cannot match our commentary voice. That is another reason to choose Voice Live.
- **Same persona block.** One `PERSONA` string, written in the guide's sections (Role, Personality & Tone, Language, Verbosity, Tools, Safety), feeds both the commentary generator and the Voice Live `instructions`. For answers, add: "calmer studio register, 1–2 sentences".
- **Shared memory:**
  - At connect, send one system item "MATCH SO FAR" (score, scorers, last 5 aired lines).
  - After that, the relay appends each aired line as `[AIRED 63:12] …`.
  - Label the items, because the guide advises marking current state versus stale background for long sessions.
  - Text context is billed as input, cached input included, so keep this rolling window small rather than the full 90 minutes.
- **No spoilers:**
  - The commentary generator may see the look-ahead.
  - The Q&A session sees only state at `listener_clock = live_clock − delay_ms`, enforced inside the tools.

### 5. Bulgarian questions and answers

| Path | Bulgarian? | Note |
|---|---|---|
| `gpt-realtime(-mini)` native audio in | Listed | The list covers languages "that exceeded <50% WER" (sic) |
| `mai-transcribe-2` (preview) | `bg` ✅ | Supports `phrase_list`. Add our synthetic player names. |
| `azure-speech` | `bg-BG` (Fast transcription ✅; custom speech plain text only) | Set `"language": "bg-BG"`. The multilingual auto mode covers 15 locales and **not** Bulgarian, and transcribes unsupported languages at "low" quality. It pairs only with **non-multimodal** models (`gpt-5.6-luna`, `gpt-4.1-mini`, …), not with `gpt-realtime*`. |
| Voice out | `bg-BG-BorislavNeural` / `KalinaNeural` | No styles. Use prosody and a custom lexicon (`custom_lexicon_url`) for name pronunciation. |

**Prompt and phrase lists:**
- Lock the language per session. Following the guide, avoid "Mirror the user", and switch only on an explicit request or a substantive utterance in another language.
- `phrase_list` is not supported on `gpt-4o-transcribe`-family models.
- Whether the `bg-BG` phrase list works under `azure-speech` is **unverified**.

### 6. Safety and cost caps

**Scope.**
- The persona answers only about this synthetic match and football basics.
- For anything else it gives a one-line redirect ("I'm just here for the match. Ask me about the score, a player or what just happened").
- No betting or odds advice.
- No web or search tool exists, so there is nothing to misuse. All tools are read-only.
- Disclose "AI voice" on first use (file 27).

**Caps** (the relay enforces them; the numbers are ours):

| Cap | Value |
|---|---|
| Answer length | `max_output_tokens` 300 |
| Questions per session | 30 |
| Tool calls per answer | 4 |
| Idle close | 90 s idle |
| Session reconnect | Reconnect at 55 min (before the 60-min limit) |
| Rate limit | One live session per fan |

**Cost estimate** (ours, using the file 27 rates and about 20 output audio tokens per second):
- A 10 s answer is about 200 Standard output tokens × $0.026/1K ≈ **$0.005**.
- Text context of about 3K tokens at the Pro text-in rate of $0.004/1K (an upper bound) is about $0.012.
- That makes about **$0.02 per question**, or about $0.60 per fan at the 30-question cap.

## So what for us

**Tely.** Stage: **Personalise and Render (two-way audio)**, with answers taken from the **Interpret** engine through MCP tools.

- **What to build:**
  - the gated toggle Ask;
  - a Voice Live relay running `gpt-realtime-2.1-mini` (Standard tier) for English;
  - the same voice as the commentary;
  - six clamped tools;
  - a pause/duck/catch-up mixer.
- **What to demo:** a blind-fan scenario. Mid-attack, the fan asks "Where's the ball?" and gets a zone answer. Then "How far has Kovač run?" gets a verified number with its evidence id. Then "…back to the action" with a catch-up line. Finally, a goal cuts into an answer.
- **The differentiator:** the spoiler-free clamp combined with "hold that thought" look-ahead. That is the "commentator who knows what is coming" made safe.

**Other ideas:**
- **D Chalk Talk:** reuses the same relay with a `draw_on_frame` tool (file 27).
- **22 Half-Time Talk:** reuses the session for its follow-up questions.
- **12 Jargon Buster:** add an `explain_term` tool.
- **C One Number:** a "what is the number now?" tool.
- **18 Agentic:** the voice session is one more MCP client, adding traceable `tools/call` spans.

**Build order:**
1. Python tools and REST.
2. Relay plus browser WebRTC in English with headphones.
3. Ducking and catch-up.
4. Bulgarian session.
5. Media Session headset toggle (bonus).

## Reuse: code & links

**a) Python tools over the delayed match state** (`match_tools.py`; MCP SDK v2 `MCPServer` per file 18; FastAPI for the relay; the `engine` API is ours)

```python
import difflib
from fastapi import FastAPI, Header, HTTPException
from mcp.server import MCPServer
from twincast.engine import engine          # deterministic stats engine (file 18)

mcp, api = MCPServer("tely-tools"), FastAPI()
PITCH_X, PITCH_Y = 105.0, 68.0

def snap(session_id: str):
    s = engine.session(session_id)                         # knows match_id + delay_ms
    return engine.state_at(s.match_id, engine.live_clock_ms(s.match_id) - s.delay_ms)  # NO look-ahead

def zone(x: float, y: float, attacking_left_to_right: bool) -> str:
    gx = x if attacking_left_to_right else PITCH_X - x
    third = "own third" if gx < 35 else "middle third" if gx < 70 else "final third"
    side = "left" if y < PITCH_Y / 3 else "right" if y > 2 * PITCH_Y / 3 else "centre"
    return f"{side} of the pitch, {third}, about {round(PITCH_X - gx)} metres from goal"

def find_player(st, q: str):
    if q.strip().isdigit():
        hits = [p for p in st.players.values() if str(p.number) == q.strip()]
    else:
        names = {p.name.lower(): p for p in st.players.values()}
        hits = [names[n] for n in difflib.get_close_matches(q.lower(), names, n=3, cutoff=0.6)]
    if len(hits) != 1:   # isError-style actionable feedback, the model asks a short question
        return None, {"error": "ambiguous_or_unknown", "candidates": [f"{p.name} ({p.team} #{p.number})" for p in hits]}
    return hits[0], None

def get_score_and_clock(session_id: str) -> dict:
    st = snap(session_id)
    return {"say": f"{st.home} {st.score[0]}, {st.away} {st.score[1]}, {st.minute}th minute",
            "clock_ms": st.clock_ms, "evidence_ids": [e.id for e in st.goals]}

def get_ball_position(session_id: str) -> dict:
    st = snap(session_id); b = st.ball
    return {"say": f"{st.possession_team} have it, {zone(b.x, b.y, st.attacks_l2r(st.possession_team))}",
            "x": b.x, "y": b.y, "evidence_ids": [st.last_event.id]}

def where_is(session_id: str, player: str) -> dict:
    st = snap(session_id); p, err = find_player(st, player)
    if err: return err
    d = ((p.x - st.ball.x) ** 2 + (p.y - st.ball.y) ** 2) ** 0.5
    return {"say": f"{p.name} is on the {zone(p.x, p.y, st.attacks_l2r(p.team))}, {d:.0f} metres from the ball",
            "evidence_ids": [f"track:{p.id}@{st.clock_ms}"]}

def get_player_stats(session_id: str, player: str, metrics: list[str] | None = None) -> dict:
    st = snap(session_id); p, err = find_player(st, player)
    if err: return err
    m = {"distance_km": round(p.distance_m / 1000, 1), "top_speed_kmh": round(p.top_speed_kmh, 1),
         "passes": f"{p.passes_completed} of {p.passes}", "shots": p.shots}
    m = {k: v for k, v in m.items() if not metrics or k in metrics}
    return {"say": f"{p.name}: " + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in m.items()),
            "metrics": m, "evidence_ids": p.evidence_ids}

def get_last_events(session_id: str, n: int = 3) -> dict:
    st = snap(session_id); ev = st.events[-max(1, min(n, 5)):][::-1]
    return {"say": " Then ".join(e.spoken for e in ev), "evidence_ids": [e.id for e in ev]}

def explain_moment(session_id: str, moment_id: str) -> dict:
    st = snap(session_id); x = engine.explanation(moment_id)          # cached, truth_check == "pass" only
    if x is None or x.clock_ms > st.clock_ms:
        return {"error": "unknown_moment", "hint": "call get_last_events first"}
    return {"say": x.text["casual"], "evidence_ids": x.evidence_ids}

def catch_up_line(session_id: str, since_ms: int) -> str:              # templated, no LLM
    st = snap(session_id); missed = [e for e in st.events if e.clock_ms > since_ms and e.priority >= 2]
    if not missed: return "Back to the action."
    top = sorted(missed, key=lambda e: -e.priority)[:2]
    return "Back to the action. While we talked, " + " and ".join(e.spoken_past for e in top) + "."

TOOLS = {f.__name__: f for f in (get_score_and_clock, get_ball_position, where_is,
                                 get_player_stats, get_last_events, explain_moment)}
for f in TOOLS.values():
    mcp.tool()(f)                                  # same functions on the MCP server (read-only)

@api.post("/voice-tools/{name}")
def call_tool(name: str, args: dict, x_session: str = Header(...)):
    if name not in TOOLS: raise HTTPException(404, "unknown tool")
    return TOOLS[name](x_session, **{k: v for k, v in args.items() if k != "session_id"})

@api.get("/catchup")
def catchup(since_ms: int, x_session: str = Header(...)):
    return {"say": catch_up_line(x_session, since_ms)}
```

**b) Relay: browser SDP ↔ Voice Live control WebSocket, tools, caps** (Node 22 TypeScript; `npm i express ws @azure/identity`; event names from the Voice Live WebRTC page)

```ts
import express from "express";
import WebSocket from "ws";
import { DefaultAzureCredential } from "@azure/identity";

const RES = process.env.FOUNDRY_RESOURCE!, TOOLS_API = process.env.TOOLS_API!;
const cred = new DefaultAzureCredential();
const fn = (name: string, description: string, properties: object = {}, required: string[] = []) =>
  ({ type: "function", name, description, parameters: { type: "object", properties, required, additionalProperties: false } });
const player = { type: "string", description: "Player name or shirt number as the fan said it" };
const TOOLS = [
  fn("get_score_and_clock", "Current score and match minute as the listener hears it."),
  fn("get_ball_position", "Which team has the ball and where it is, in spoken zone words."),
  fn("where_is", "Where one player is now, relative to goal and ball.", { player }, ["player"]),
  fn("get_player_stats", "Verified stats for one player so far.", { player,
     metrics: { type: "array", items: { type: "string", enum: ["distance_km", "top_speed_kmh", "passes", "shots"] } } }, ["player"]),
  fn("get_last_events", "The most recent events, newest first.", { n: { type: "integer", minimum: 1, maximum: 5 } }),
  fn("explain_moment", "Why a recent moment mattered. Use an id from get_last_events.", { moment_id: { type: "string" } }, ["moment_id"]),
];
const PERSONA = `# Role and Objective
You are the match commentator for a blind or low-vision fan, answering their questions mid-match.
# Personality and Tone
Warm, vivid, calm studio register for answers. 1-2 short sentences. One idea per sentence.
# Tools
Every number, name, position or event MUST come from a tool result in this turn. Do not invent, assume,
simulate, or rename tools. If a tool returns candidates, ask one short question. Never say what happens next.
# Scope
Only this match and football basics. Otherwise give one friendly redirect. No betting advice.`;

const app = express(); app.use(express.json({ limit: "64kb" }));
app.post("/voice/offer", async (req, res) => {
  const { sdp, sessionId, lang } = req.body as { sdp: string; sessionId: string; lang: "en" | "bg" };
  const { token } = (await cred.getToken("https://ai.azure.com/.default"))!;
  const ws = new WebSocket(`wss://${RES}.services.ai.azure.com/voice-live/realtime/calls` +
    `?api-version=2026-01-01-preview&model=gpt-realtime-2.1-mini`, ["realtime"],
    { headers: { Authorization: `Bearer ${token}` } });
  const names = new Map<string, string>(); let toolCalls = 0;
  const kill = setTimeout(() => ws.close(), 55 * 60_000);          // under the 60-min session limit
  ws.on("open", () => ws.send(JSON.stringify({
    type: "rtc.call.sdp.create", sdp_offer: sdp,
    session: {
      modalities: ["text", "audio"], tools: TOOLS, tool_choice: "auto",
      instructions: PERSONA + (lang === "bg" ? "\n# Language\nThe conversation is only in Bulgarian." :
                                              "\n# Language\nEnglish is the default response language."),
      voice: lang === "bg" ? { type: "azure-standard", name: "bg-BG-BorislavNeural" }
                           : { type: "azure-standard", name: "en-GB-Ollie:DragonHDLatestNeural", rate: "1.1" },
      input_audio_noise_reduction: { type: "azure_deep_noise_suppression" },
      // gpt-realtime* hears audio natively; this transcript is for captions/logs. azure-speech only pairs with
      // non-multimodal models (e.g. gpt-5.6-luna), so with a realtime model use mai-transcribe-2 for Bulgarian.
      input_audio_transcription: lang === "bg" ? { model: "mai-transcribe-2", language: "bg" } : undefined,
      turn_detection: lang === "bg" ? { type: "server_vad", silence_duration_ms: 500 }
                                    : { type: "azure_semantic_vad", silence_duration_ms: 500, remove_filler_words: true },
    },
  })));
  ws.on("message", async (raw) => {
    const m = JSON.parse(raw.toString());
    if (m.type === "rtc.call.sdp.created") return void res.json({ sdp: m.sdp_answer });
    if (m.type === "rtc.call.error" || m.type === "error") { console.error(m); if (!res.headersSent) res.status(502).end(); return; }
    if (m.type === "response.output_item.added" && m.item?.type === "function_call") names.set(m.item.call_id, m.item.name);
    if (m.type === "response.function_call_arguments.done") {
      const name = m.name ?? names.get(m.call_id);                   // name may arrive either way (docs ambiguous)
      let output: unknown = { error: "tool_budget_exceeded" };
      if (++toolCalls <= 120) {                                        // per-session cap (ours)
        const r = await fetch(`${TOOLS_API}/voice-tools/${name}`, { method: "POST",
          headers: { "content-type": "application/json", "x-session": sessionId }, body: m.arguments || "{}" });
        output = r.ok ? await r.json() : { error: `tool_failed_${r.status}` };
      }
      ws.send(JSON.stringify({ type: "conversation.item.create",
        item: { type: "function_call_output", call_id: m.call_id, output: JSON.stringify(output) } }));
      ws.send(JSON.stringify({ type: "response.create" }));
    }
  });
  ws.on("close", () => clearTimeout(kill));
  sessions.set(sessionId, ws);                                         // for injecting aired commentary
});
const sessions = new Map<string, WebSocket>();
export function onCommentaryAired(sessionId: string, clock: string, text: string) {   // shared context
  sessions.get(sessionId)?.send(JSON.stringify({ type: "conversation.item.create",
    item: { type: "message", role: "system", content: [{ type: "input_text", text: `[AIRED ${clock}] ${text}` }] } }));
}
app.listen(8080);
```

**c) Browser: WebRTC, gated toggle Ask, ducking hook, catch-up** (TypeScript; the mixer gains come from the file 27 Web Audio graph)

```ts
type State = "LIVE" | "LISTENING" | "THINKING" | "ANSWERING" | "RESUMING";
let state: State = "LIVE", qaStartedClockMs = 0;
declare const ctx: AudioContext, crowdGain: GainNode, answerGain: GainNode;
declare const commentary: { pause(): void; resume(): void; say(text: string): Promise<void>; clockMs(): number };
declare function earcon(kind: "listen" | "sent"): void;

export function duckForQA(on: boolean) {            // fast down, slow up (file 27: ~95% after 3 time constants)
  crowdGain.gain.setTargetAtTime(on ? 0.15 : 1.0, ctx.currentTime, on ? 0.05 : 0.5);
  on ? commentary.pause() : commentary.resume();     // pause speech; never overlap two voices
}

export async function connectVoice(sessionId: string, lang: "en" | "bg") {
  const pc = new RTCPeerConnection();
  const mic = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  const track = mic.getAudioTracks()[0]; track.enabled = false;           // gated: silent until Ask
  pc.addTrack(track, mic);
  const dc = pc.createDataChannel("voice-live-events");                   // before createOffer
  const analyser = ctx.createAnalyser();
  pc.ontrack = (e) => {
    const el = new Audio(); el.srcObject = e.streams[0]; el.muted = true; el.play();   // Chrome workaround (forum reports)
    ctx.createMediaStreamSource(e.streams[0]).connect(answerGain).connect(analyser).connect(ctx.destination);
  };
  await pc.setLocalDescription(await pc.createOffer());
  await new Promise<void>((r) => { if (pc.iceGatheringState === "complete") r();
    pc.onicegatheringstatechange = () => pc.iceGatheringState === "complete" && r(); setTimeout(r, 3000); });
  const { sdp } = await (await fetch("/voice/offer", { method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ sdp: pc.localDescription!.sdp, sessionId, lang }) })).json();
  await pc.setRemoteDescription({ type: "answer", sdp });
  const send = (o: object) => dc.readyState === "open" && dc.send(JSON.stringify(o));

  dc.onmessage = async (e) => {
    const m = JSON.parse(e.data);
    if (m.type === "input_audio_buffer.speech_stopped" && state === "LISTENING") { track.enabled = false; state = "THINKING"; earcon("sent"); }
    if (m.type === "response.created") state = "ANSWERING";
    if (m.type === "response.done" && state === "ANSWERING") {
      await untilSilent(analyser, 600);                                    // response.done != playback finished
      state = "RESUMING"; duckForQA(false);
      const { say } = await (await fetch(`/catchup?since_ms=${qaStartedClockMs}`, { headers: { "x-session": sessionId } })).json();
      await commentary.say(say); state = "LIVE";
    }
  };

  const askBtn = document.querySelector<HTMLButtonElement>("#ask")!;      // <button id="ask" aria-pressed="false">Ask</button>
  const toggle = () => {
    if (state === "LISTENING") { track.enabled = false; state = "THINKING"; earcon("sent"); askBtn.ariaPressed = "false"; return; }
    if (state === "ANSWERING") { send({ type: "response.cancel" }); send({ type: "output_audio_buffer.clear" }); } // stop / barge-in
    qaStartedClockMs = commentary.clockMs(); duckForQA(true); earcon("listen");
    setTimeout(() => { track.enabled = true; state = "LISTENING"; }, 250); // keep screen-reader echo out of the mic
    askBtn.ariaPressed = "true";
  };
  askBtn.onclick = toggle;
  try { navigator.mediaSession.setActionHandler("pause", toggle); navigator.mediaSession.setActionHandler("play", toggle); } catch {}
  return { pc, dc, send };
}

async function untilSilent(a: AnalyserNode, quietMs: number) {
  const buf = new Float32Array(a.fftSize); let quietSince = performance.now();
  while (performance.now() - quietSince < quietMs) {
    a.getFloatTimeDomainData(buf);
    const rms = Math.sqrt(buf.reduce((s, v) => s + v * v, 0) / buf.length);
    if (rms > 0.01) quietSince = performance.now();                       // threshold: tune by ear
    await new Promise((r) => setTimeout(r, 50));
  }
}
```

**Links**
- Voice Live samples, including JS WebRTC/avatar, Live-Reference AEC and Python function calling: https://github.com/microsoft-foundry/voicelive-samples
- Standalone browser WebRTC sample: on the Voice Live WebRTC Learn page (see Sources)

## Sources

- Voice Live API with WebRTC (endpoint, SDP events, three channels, event routing) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-webrtc — accessed 20 Oct 2026
- How to use the Voice Live API (auth, session, turn detection, transcription models, voices, HD routing, rate) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-how-to — accessed 20 Oct 2026
- Voice Live API overview (models, tiers, function calling, tokens per second) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live — accessed 20 Oct 2026
- Voice Live API language support (Bulgarian, multilingual auto-detect list, MAI Transcribe) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-language-support — accessed 20 Oct 2026
- How to customize Voice Live input and output (phrase list, custom lexicon) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-how-to-customize — accessed 20 Oct 2026
- Quotas and limits for Azure Speech (Voice Live connections, 60-min session, TPM) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-services-quotas-and-limits — accessed 20 Oct 2026
- Language and voice support (bg-BG STT row, Bulgarian voices) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support — accessed 20 Oct 2026
- Azure OpenAI Realtime API reference (follows the OpenAI spec) — https://learn.microsoft.com/en-us/azure/foundry/openai/realtime-audio-reference — accessed 20 Oct 2026
- OpenAI Realtime conversations guide (tools, function_call_output, truncate, push-to-talk, 60-min session) — https://developers.openai.com/api/docs/guides/realtime-conversations — accessed 20 Oct 2026
- OpenAI Realtime client events (message roles, response.create fields, output_audio_buffer.clear) — https://developers.openai.com/api/reference/resources/realtime/client-events — accessed 20 Oct 2026
- OpenAI Realtime server events (output_audio_buffer.started/stopped, usage) — https://developers.openai.com/api/reference/resources/realtime/server-events — accessed 20 Oct 2026
- OpenAI, Prompting realtime voice models (sections, preambles, verbosity, language lock, tool rules) — https://developers.openai.com/api/docs/guides/voice-prompting — accessed 20 Oct 2026
- MCP specification 2025-11-25, Tools (schemas, isError, security considerations) — https://modelcontextprotocol.io/specification/2025-11-25/server/tools — accessed 20 Oct 2026
- Anthropic, Writing effective tools for agents — https://www.anthropic.com/engineering/writing-tools-for-agents — accessed 20 Oct 2026
- Apple, Use VoiceOver gestures on iPhone (two-finger double tap, pass-through gesture, two-finger tap) — https://support.apple.com/guide/iphone/use-voiceover-gestures-iph3e2e2281/ios — accessed 20 Oct 2026
- Google, Customize Android settings for TalkBack (audio ducking on by default) — https://support.google.com/accessibility/android/answer/6283655 — accessed 20 Oct 2026
- MDN, MediaSession.setActionHandler() — https://developer.mozilla.org/en-US/docs/Web/API/MediaSession/setActionHandler — accessed 20 Oct 2026
- Google Conversation Design, Confirmations — https://developers.google.com/assistant/conversation-design/confirmations — accessed 20 Oct 2026
- Amazon Alexa Voice Design Guide, What Alexa says (one-breath test) — https://developer.amazon.com/fr/designing-for-voice/what-alexa-says/ — accessed 20 Oct 2026
- Alexa blog, Things every Alexa skill should do: pass the one-breath test — https://developer.amazon.com/blogs/alexa/post/531ffdd7-acf3-43ca-9831-9c375b08afe0/things-every-alexa-skill-should-do-pass-the-one-breath-test — accessed 20 Oct 2026
- Abdolrahmani, Kuber, Branham, "Siri Talks at You" (ASSETS 2018), abstract — https://doi.org/10.1145/3234695.3236344 — accessed 20 Oct 2026
- Vtyurina et al., VERSE: Bridging screen readers and voice assistants (ASSETS 2019) — https://cs.uwaterloo.ca/~avtyurin/papers/VERSEVtyurinaASSETS2019.pdf — accessed 20 Oct 2026
- Stivers et al., Universals and cultural variation in turn-taking in conversation (PNAS 2009) — https://pmc.ncbi.nlm.nih.gov/articles/PMC2705608/ — accessed 20 Oct 2026
- Babylon.js forum, remote WebRTC track silent in Web Audio unless a media element plays it (anecdotal) — https://forum.babylonjs.com/t/sound-created-with-a-remote-webrtc-stream-track-does-not-seem-to-work/7047 — accessed 20 Oct 2026
