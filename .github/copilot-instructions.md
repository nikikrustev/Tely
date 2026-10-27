# Tely — Copilot instructions

Audio-first match experience for blind and low-vision fans. SYNTHETIC match data only: never add real
Premier League data, names, crests, chants or copyrighted audio. Fictional clubs and players, CC0 crowd clips,
and every AI voice is labelled as AI. No GPL or AGPL code, dependencies or build tools.

## Where things are
Read `docs/architecture.md` for the code map and the seams, and `docs/DECISIONS.md` for why.

## Stack
- Python 3.12 package `tely` in `pipeline/`: generator, interpret, commentary, agents, eval, bundle
  builder; the Q&A tools in `tely/qa/`. Tests: `cd pipeline && pytest` (finds `tests/`).
- Azure SDKs (Speech, Identity, openai, Agent Framework) go in `pipeline/requirements-azure.txt` only, never in
  `pyproject.toml`. CI never installs them; tests mock the synthesiser and the model.
- TypeScript (Vite, vanilla, strict) in `web/`. Tests: `cd web && npm test` (vitest, `tests/`).
  The commentary track and live Ask live in `web/src/voice/`; `web/src/main.ts` calls `mountLaneA()` once.
- Stage 7 relay (FastAPI, Voice Live) in `relay/`. It imports `tely.qa`; never copy the tools.
- Infra: Bicep in `infra/`, deployed with `azd` (env `judge`, `rg-as-judge`, Sweden Central; Static Web Apps in eastus2).

## Rules
- Numbers shown or spoken to users come from the stats tools, never invented by an LLM.
- Spoiler firewall: Q&A tools and the browser only see state at or before the playhead (`playhead_s`).
  The relay injects the playhead; the model never sets the clock.
- Cues follow the cue format in `stoynev research/43-tely-architecture.md` §3. Commentary cues live in
  `cues.*.jsonl`; `segments.json` carries no cues.
- The English HD voice is en-US DragonHD: no `<prosody>` or `express-as`, use `[style]` tags and `<break>`. Other
  languages use BrianMultilingual with `<lang>` and `<prosody>` (D27).
  Never re-synthesise a cached SSML hash.
- Audio: one shared AudioContext; never start audio without a user gesture; duck with GainNode ramps
  (`setTargetAtTime`), no abrupt gain jumps; respect `prefers-reduced-motion` for haptics.
- Accessibility: every visual element has an aria-live or text equivalent; test with the keyboard only.
- No secrets in code or logs. Azure auth is `DefaultAzureCredential` / managed identity; keys only from a git-ignored `.env`.
- Keep PRs small; add or update tests in the same PR; explain trade-offs in the PR description.
