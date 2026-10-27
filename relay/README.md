# relay/ (Stage 7, owner: A, potencialbg)

One FastAPI container. It runs the fan's live spoken questions through Foundry Voice Live and hosts B's Stats MCP server.
B's Q&A brain (`tely.qa`) is **imported, never copied**, so the playhead clamp that B tests is the code that runs live.

| Route | What |
|---|---|
| `GET /health` | `{"ok", "mode"}`. The page calls it on load to wake the scaled-to-zero replica (D6). |
| `WS /voice` | One fan's live Ask. Text frames are JSON, binary frames are PCM16 mono 24 kHz (mic up, answer down). |
| `POST /mcp` | B's `tely.qa.mcp_server`, streamable HTTP, stateless. Playhead from the `X-Tely-Playhead` header. |
| `POST /feedback` | Tester mode (`?test=1`, D19). One flat JSON event (`feedback.py` schema, 4 KB max), logged as the App Insights custom event `tester_feedback` (`telemetry.py`). Only `FEEDBACK_ORIGINS` may post; 60 per IP per 10 min, `DAILY_FEEDBACK_CAP` a day. No IP in the event. |

**`/voice` messages.**
- Browser → relay: `{"type":"ask","playhead_s"}`, binary mic audio, `{"type":"commit"}`, `{"type":"cancel"}`, `{"type":"metrics","client_latency_ms"}`.
- Relay → browser: `ready`, `listening`, `speech_started`, `speech_stopped`, `tool` (`name`, `say`, `prefs`), binary answer audio, `answer_done` (`turn` = the golden record), `refusal` (`reason`, `clip`, `say`), `error`, `closed`.

**The clock.** The playhead comes only from the browser's `ask`, clamped to the cut. The relay injects it into every `call_tool()`; no tool schema has a clock argument, and B's `tools.call` drops a `playhead_s` the model might invent.

**Caps** (`caps.py`, our numbers, file 40 §6 and file 21):
- 30 questions per session, 4 tool calls per answer (then the next response gets `tool_choice: "none"`), close after
  90 s idle, a fresh Voice Live connection after 55 min;
- a session lasts at most 10 minutes however busy it is, and sends at most ~2 minutes of mic audio; the relay ends a
  turn itself 12 s + 3 s grace after the first audio (or after `speech_started`) if the browser hasn't; one WebSocket
  frame is at most 64 KB (`uvicorn --ws-max-size 65536`);
- 200 questions a day (`DAILY_QUESTION_CAP`) and 20 a day per IP (`DAILY_QUESTION_CAP_PER_IP`). A question counts once
  Voice Live has heard it (a transcript or a response), not when the `ask` arrives;
- per IP: 6 sessions per 10 minutes and 2 open at once; 60 MCP calls a minute. The IP is the rightmost
  `X-Forwarded-For` entry (the one the Container Apps ingress adds), never the client's own leftmost one;
- `/voice` needs an `Origin` header from `ALLOWED_ORIGINS` (browsers always send one; `eval/qa_latency.py run` needs `--origin`);
- `DEMO_MODE=off` turns live Ask off, and the presets take over.

The counters are in memory, per replica: they reset whenever the relay starts again, which includes every cold start
after scaling to zero (D6), and with 2 replicas each counts on its own. That is deliberate (no storage, no cost); the
budget alert in `infra/main.bicep` (`BUDGET_EMAIL`) and the free account's spending limit are the backstop.

Every refusal is spoken, from a clip rendered in the commentary voice (`clips.py` → `render_clips.py`).

**Run locally** (A's machine, `az login`; from the repo root):

```bash
pip install -e "./pipeline[mcp]" -r relay/requirements.txt
FOUNDRY_RESOURCE=<name> PYTHONPATH="pipeline;." uvicorn relay.app:app --port 8080   # ":" instead of ";" on Linux/macOS
```

Then open the site at `http://localhost:5173/?debug=1&relay=http://localhost:8080`.

**Tests** (no Azure packages, no keys; CI job `relay`): `cd relay && pytest`.

**After a live session:** run `python -m relay.golden_from_logs --since 3h`, which appends to `eval/live/live_<date>.jsonl`. Then tell Nikolay.

**Latency:** run `python eval/qa_latency.py run|browser|summarise`, then `python eval/build_report.py`.
