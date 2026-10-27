# Architecture

One event stream, five stages, three places it runs. The diagram is in the [README](../README.md#architecture-what-shipped);
this page is the map of the code and the seams between its parts.

## Where things run

| Part | Runs | Code |
|---|---|---|
| Build: match, signals, commentary, voice, bundle | once, on a developer machine (`az login`, keyless) | `pipeline/tely/` |
| The replay | the fan's browser, from static files on Azure Static Web Apps | `web/` |
| Live questions and the MCP server | Azure Container Apps, scales to zero | `relay/` |
| Infrastructure | Bicep through `azd` | `infra/`, `azure.yaml` |

## The seams

These are the interfaces where one part's output is another's input. Each one has a test that fails if either side
drifts.

1. **The match format**, written by `pipeline/tely/build_match.py` and read by the commentary, the Q&A tools and the
   page: `meta.json`, `events.jsonl` (CDF), `signals.json`, `ticks.json.gz`. See [match-format.md](match-format.md);
   tested by `pipeline/tests/test_contract.py` against `pipeline/sample_match/`.
2. **The Q&A tools** (`pipeline/tely/qa/`): one set of playhead-clamped functions behind the offline quick questions
   (a copy in `web/src/ask/local-tools.ts`), the live voice (Voice Live function calls in `relay/voicelive.py`) and
   the MCP server (`qa/mcp_server.py`). `pipeline/tests/golden/qa_cases.jsonl` holds their exact answers at many
   playheads. pytest and vitest both replay it, so the Python and TypeScript copies never drift.
3. **The page's two halves**: `web/src/voice/` (the commentary track and the live Ask) and the rest of `web/src/` (the
   stadium, quick questions, settings, haptics). They meet only through the interfaces in `web/src/contracts/voice.ts`
   and `web/src/contracts/stage.ts`. Both are append-only.
4. **The bundle** (`web/public/replay/v1/judge/`): everything the browser plays is a static file listed, with its
   sha256, in `manifest.json`. That includes the cue track per language, the MP3s, the answers, the Director's notes
   and the overlays. `pipeline/tests/test_bundle.py` checks that a rebuild is byte-identical.
5. **The evals** (`eval/`): `report.json` merges every measurement (`python -m tely.eval`, `eval/qa.json`,
   `eval/planted.json`, `eval/speed.json`, `eval/listening.json`) and `eval/build_report.py` renders `report.md`.
6. **Live golden turns** (`eval/live/`): what the relay recorded for each live question (question, tool calls,
   answer, latency; no keys, tokens or audio). `pipeline/tests/test_live_golden.py` replays every tool call.

## Folders

```
web/        the player: src/voice (commentary track, live Ask), src/ask (quick questions), src/audio (crowd, mix,
            mono, tones), src/notes (Director's notes), src/tester, tests/ (vitest *.test.ts, Playwright + axe *.spec.ts)
pipeline/   tely/ (generator, signals, commentary, agents, qa, eval), tests/ (pytest, golden/), sample_match/
relay/      FastAPI relay: Voice Live, the MCP server, feedback; tests/
infra/      Bicep
eval/       measurements and the report; live/ golden turns; soak/ the 90-minute runs
video/      the demo video's script, shot list, captions and screens
assets/     crowd sound sources and licences, and the script that cut them
docs/       DECISIONS.md (every decision, dated), architecture.md, match-format.md
```
