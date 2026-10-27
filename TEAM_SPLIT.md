# Tely: two-person split (20 Oct 2026)

_This file is for both people **and both Claude Code sessions**. If you are Claude, read all of it before you touch any file._

**People:**
- **A = potencialbg.** A owns everything Microsoft.
- **B = Nikolay.** B's lane has no Microsoft.

Nikolay's GitHub account is `nikikrustev`, the repo owner (confirmed by potencialbg, 20 Oct 2026). `.github/CODEOWNERS` uses it.

**How this relates to `BUILD_PLAN.md`:** this file is an add-on. The stage prompts and "Done when" checks still come from `BUILD_PLAN.md`.
- If the two disagree on **who** does something or **which file** it goes in, this file wins.
- On **what** to build and **when**, `BUILD_PLAN.md` wins.

Hours come from the plan's stage estimates. Dividing them between A and B is my own estimate.

## The two rules

1. **Only A touches Microsoft services** (definition below).
2. **One file, one owner.** Every file in the repo has exactly one owner, listed in "File ownership". A Claude session edits **only** files its person owns. Both Claudes can then run at the same time, on their own branches, and their PRs never conflict. If you need a change in the other person's file, write it under a `HANDOFF to <A|B>` heading in your PR description. Don't edit the file.

## Verdict: is this a perfect split?

Nikolay proposed: "I take the Q&A agent and its tools; you take the commentator and speech-to-text/text-to-speech." That keeps all Microsoft work with A, but only after one reinterpretation and one addition.

1. **The Q&A model sits in A's lane.** Live Q&A runs on **Foundry Voice Live**, which does speech-to-text, the LLM and text-to-speech in one Microsoft service (files 40, 43).
   - B owns the agent's **brain**:
     - the 8 tools, clamped to the playhead;
     - the persona prompt;
     - a deterministic question router with no LLM;
     - catch-up and "hold that thought";
     - the MCP server;
     - the Q&A eval questions.
   - A **hosts** that brain inside Voice Live.
2. **B also takes the stages that use no Microsoft service.** Q&A alone is about 9 h of a 55 h plan. B therefore also builds:
   - the synthetic match and signals (Stage 1), so B defines the event format Nikolay asked for;
   - the browser sound stage (Stage 2);
   - haptics, settings and the UI;
   - the offline Ask;
   - accessibility and the listening test.

**Result: about 29 h for A and 26.5 h for B.** This is the best split I found, but it isn't perfect. Three seams remain:

| Seam | Why it stays | Fix |
|---|---|---|
| B can't run the real Q&A model end to end | The model is Voice Live, which is Microsoft | B's no-LLM router is both the test harness and the offline fallback. A saves live-session transcripts in `contracts/golden/a/`, and B turns them into regression tests. |
| Spoken fragments need Azure TTS | TTS is Microsoft | B writes the **text** (`FRAGMENTS`). A renders the audio. |
| A's commentator (Stage 3) needs B's match data on Wed | The critical path crosses lanes | B publishes `contracts/b/` with a hand-written 90 s sample today. A builds against the sample on Wed and switches when B's Stage 1 merges. |

**Alternatives I rejected:**
- **B does Q&A only:** about 9 h for B against 46 h for A.
- **File 43's split by language:** the Voice Live browser client and the relay would land with the TypeScript person, which breaks rule 1.
- **B owns Microsoft:** the Azure account, quota request and Stage 0 are A's job today, and Nikolay asked A to take the speech work.

## What counts as "Microsoft software"

**A only.** This means anything that needs a Microsoft or Azure sign-in or credential, or that we will name as Microsoft tech in the pitch:
- the Azure portal, `az`/`azd`, Bicep and budgets;
- Foundry: models, **Agent Framework**, **Voice Live**, **Azure Speech** (TTS and STT), evaluators and tracing;
- Static Web Apps, Container Apps, ACR and Application Insights;
- GitHub Copilot Agent Mode and the Azure MCP Server;
- `.github/` workflows;
- Clipchamp, the Snipping Tool recorder and Windows Narrator testing.

**Both may use these:**
- GitHub as a plain git host: branches, PRs, reviews;
- TypeScript, Node and npm;
- the Playwright library;
- VS Code as a plain editor, with no Copilot.

**B must never:**
- hold a Microsoft key or see a `.env` with values;
- run `az` or `azd`;
- install `azure-*`, `@azure/*`, `agent-framework` or `openai` packages.

## File ownership

**Paths and how this differs from BUILD_PLAN.md.** Paths here override the plan where they differ. There are four differences, all made so that no file has two owners:
1. A's browser code lives in `web/src/lane-a/`, not `web/src/audio/commentary-track.ts` or `web/src/ask/live-ask.ts`.
2. **`segments.json` no longer carries cues.** A's commentary track loads `cues.en.radio.jsonl` itself. The plan's Stage 4 step "merge cues into segments.json" is dropped.
3. Tests are split by folder: `pipeline/tests/a/`, `pipeline/tests/b/`, `web/tests/a/` and `web/tests/b/`.
4. A's Azure Python packages go in `pipeline/requirements-azure.txt`, not in `pyproject.toml`.

> **Handover, 24 Oct 2026:** Nikolay has handed over his lane. **A (potencialbg) now owns every path under "B owns (Nikolay)"
> as well**, so A's Claude may edit them. The no-Microsoft rule still applies to those files: B's Python and TS must still
> run with no keys and no Azure packages, because CI and the offline Ask depend on that.

### A owns (potencialbg)

| Area | Paths |
|---|---|
| Infra and CI | `infra/**`, `azure.yaml`, `.github/**` (incl. `CODEOWNERS`), `.vscode/**`, `web/staticwebapp.config.json`, root `.gitignore`, `.gitattributes`, `.dockerignore` (added 23 Oct, A7: the relay image's build context), `.env.example` |
| Scripts | `scripts/bootstrap_azure.sh`, `scripts/smoke_azure.py` |
| Python, commentator and agents | `pipeline/tely/__init__.py` (empty; created once in Stage 0, never edited), `pipeline/tely/commentary/**`, `pipeline/tely/agents/**`, `pipeline/tely/build_commentary.py`, `pipeline/tely/build_bundle.py`, `pipeline/tely/answers.py`, `pipeline/tely/spoiler.py`, `pipeline/tely/voices.py`, `pipeline/tely/eval/**`, `pipeline/requirements-azure.txt`, `pipeline/tests/a/**` |
| Relay | `relay/**`. It **imports** B's `tely.qa`; it never copies it |
| Browser | `web/src/lane-a/**` (`index.ts` with `mountLaneA()`, `commentary-track.ts`, `live-ask.ts`), `web/src/contracts/a-exports.ts`, `web/src/tester/**` (added 24 Oct, D19 tester mode), `web/tests/a/**` |
| Generated bundle files | In `web/public/replay/v1/judge/`: `cues.*.jsonl`, `audio/**`, `captions_sdh.vtt`, `descriptions.vtt`, `manifest.json`, `answers/**`, `live/**` (added 23 Oct, A7: the live Ask's refusal clips) |
| Contracts | `contracts/golden/a/**` (live Voice Live transcripts) |
| Eval and ship | `eval/report.md`, `eval/report.json`, `eval/qa_latency.py`, `eval/build_report.py`, `eval/pull_feedback.py` (added 24 Oct, D19), `video/**`, `README.md`, `SUBMISSION.md`, `docs/DECISIONS.md` |
| Shared docs (A edits, B proposes) | `CLAUDE.md`, `BUILD_PLAN.md`, `TEAM_SPLIT.md`, `stoynev research/**` |

### B owns (Nikolay)

| Area | Paths |
|---|---|
| Python, match and signals | `pipeline/pyproject.toml`, `pipeline/tely/{generator,movement,clock,interpret,crowd,haptics,judge_cut,build_match,build_segments}.py`, `pipeline/judge_cut.json`, `pipeline/tests/b/**` |
| Python, Q&A brain | `pipeline/tely/qa/**` (`__init__.py` API, `tools.py`, `router.py`, `persona.py`, `fragments.py`, `mcp_server.py`) |
| Crowd assets | `scripts/prepare_crowd.py`, `assets/**`, `web/public/crowd/**` |
| Browser | `web/package.json` + lockfile, `web/vite.config.*`, `web/playwright.config.ts` (added 24 Oct, Stage 8 a11y tests), `web/tsconfig.json`, `web/index.html`, `web/src/main.ts`, `web/src/wire.ts`, `web/src/audio/**`, `web/src/replay/**`, `web/src/haptics/**`, `web/src/ask/**`, `web/src/settings.ts`, `web/src/radar/**`, `web/src/learn/**`, `web/src/contracts/b-exports.ts`, `web/tests/b/**` |
| Generated bundle files | In `web/public/replay/v1/judge/`: `meta.json`, `events.jsonl`, `ticks.json.gz`, `signals.json`, `segments.json`, `.gitattributes` (added 21 Oct, PR #5) |
| Contracts | `contracts/README.md`, `contracts/b/**` (match format + sample), `contracts/golden/b/**` (`qa_cases.jsonl`) |
| Eval | `eval/qa_cases.jsonl`, `eval/qa.json`, `eval/listening_test.*`, `eval/listening.json`, `eval/score_listening.py` |
| Notes | `docs/nikolay/**` (B's decisions and research notes) |

**Any file not in these lists:** the person who creates it owns it, and adds it to their list through a PR to `TEAM_SPLIT.md`, which A merges.

### The cross-lane rules

These are the only places where the lanes meet:

- **Stage 0 creates the skeleton once.** A's Stage 0 creates the scaffold **including stubs of B's files**: `pyproject.toml`, `web/` Vite setup, `main.ts` calling `mountLaneA()`, `b-exports.ts`, and `qa/__init__.py` with the API signatures raising `NotImplementedError`. **From the moment that PR merges, each file belongs to the owner above.** B waits for the merge before touching `pipeline/` or `web/` (about 30 min), and works on `contracts/b/` in the meantime.
- **Generated files must be deterministic.** A's `build_bundle` reruns B's `build_match`. B's determinism test (identical sha256 on every run) means B's generated files come out byte-identical and never show as changed in A's commits. If `git status` shows B's generated files modified after A builds, that's a bug. Tell B, and don't commit them.
- **Interface files are append-only after Wed 21 at 18:00 Sofia.** That covers `contracts/b/`, `a-exports.ts`, `b-exports.ts` and the `qa/__init__.py` API. Adding a field is fine. Renaming or removing one needs the other person's approval in the PR.
- **One Claude per checkout.** If one person runs two Claude sessions at once, give each its own git worktree.

## The seams, as contracts

1. **Match data** (`contracts/b/`, B). This is the event format Nikolay asked for.
   - **`events.jsonl`:** CDF v0.3.2 event lines in the validated shape from file 26, with fictional players, metres and the origin at the centre spot.
   - **`meta.json`:** teams, players, kits, kick-off and the judge-cut window.
   - **`signals.json`:**
     - per second: win probability, suspense, tension, danger and crowd H/A;
     - per event: `xg`, `priority`, `spoken`, `spoken_past` and `zone`.

     These extras stay out of the CDF lines so the events still pass the validator.
   - **`ticks.json.gz`:** the ball at 25 Hz, and the players at a rate B picks (at least 1 Hz, so `where_is` works).
   - Also include a **hand-written 90 s sample** with a pass chain, a shot, a save and a goal, plus a validator test.
2. **The Q&A brain API** (B owns it in `pipeline/tely/qa/__init__.py`; A's relay imports it):
   ```python
   TOOL_SCHEMAS: list[dict]   # the 8 file-43 §3 schemas, Voice Live "function" format
   PERSONA: str               # Voice Live instructions (file 40 §4 and §6)
   FRAGMENTS: list[dict]      # [{id, text}]: every fixed phrase that needs audio; A renders it
   def call_tool(name: str, args: dict, *, playhead_s: float, bundle) -> dict
       # -> {say, evidence_ids, as_of_clock} | {error, candidates}; never reads past playhead_s
   def answer_text(question: str, *, playhead_s: float, bundle) -> dict   # deterministic router, no LLM
   def catch_up(since_s: float, until_s: float, bundle) -> str
   def hold_that_thought(playhead_s: float, bundle) -> bool               # says THAT, never WHAT
   ```
   A's relay injects `playhead_s` from the session, so the model never sets the clock.
3. **Browser.**
   - `web/src/contracts/b-exports.ts` (B) declares:
     - `CrowdBus.duck(db, rampMs)` / `unduck(rampMs)`;
     - `Ask.registerLiveMode(handler)`;
     - the replay clock.
   - `web/src/contracts/a-exports.ts` (A) declares:
     - `CommentaryTrack.pause()`, `resume()` and `nextCueWithin(s)`;
     - `mountLaneA(ctx)`.
   - B's `main.ts` calls `mountLaneA` once, and nothing else of A's.
4. **Golden cases.**
   - `contracts/golden/b/qa_cases.jsonl` (B) holds `{tool, args, playhead_s, expected_say}`. B's pytest and vitest both run against it, so the Python and TypeScript tools say the same thing.
   - `contracts/golden/a/live_<date>.jsonl` (A) holds real Voice Live sessions: question, tool calls with args, results, spoken answer and latency. It has no keys and no audio.
5. **Eval.**
   - B writes `eval/qa.json` and `eval/listening.json`.
   - A's `eval/build_report.py` merges everything into `eval/report.md`.

## Lanes by stage

| Stage | A (Microsoft) | B (Nikolay, no Microsoft) | Hours A / B |
|---|---|---|---|
| 0 | Accounts, quota, bootstrap, smoke test, scaffold with stubs for both lanes, CI, CODEOWNERS | `contracts/b/` v0 + 90 s sample | 2.5 / 1 |
| 1 | Review the contract PR | **All of it** | 0 / 5 |
| 2 | (none) | **All of it** | 0 / 6 |
| 3 | **All of it** (templates, planner, verifier, spoiler-leak, SSML, HD TTS) | Review that the templates read the signals correctly | 7 / 0 |
| 4 | `build_bundle`, `lane-a/commentary-track.ts`, Bicep, `azd up`, insurance video | `haptics.ts`, `settings.ts`, UI | 3.5 / 2.5 |
| 5 | **All of it** (Director on Foundry, tracing, eval) | (none) | 4 / 0 |
| 6 | `answers.py` renders B's `FRAGMENTS` | `local-tools.ts`, `ask.ts`, `FRAGMENTS`, property test | 1 / 3 |
| 7 | Relay hosting `qa/`, Voice Live, Container Apps, `lane-a/live-ask.ts`, latency eval, `mcp.json`, Copilot evidence | `qa/` package, MCP server, 20+ eval questions | 4.5 / 2.5 |
| 8 | Uptime workflow, wiring B's Playwright tests into CI, Narrator walkthrough | Radar, learn-the-sounds, Bluetooth calibration, Playwright + axe tests, listening kit + test, TalkBack/VoiceOver | 0.5 / 3.5 |
| 9 | README, SUBMISSION, Clipchamp edit, YouTube, submit | Video script, shot list, SRT captions, listener footage, link and licence checks | 6 / 3 |
| **Total** | | | **29 / 26.5** |

Each person has about 56 h, so each lane has about 25 h spare. **Use it to bring the timeline forward and protect Stage 7, not to add scope.** If you're genuinely ahead, take items back from the plan's drop list:
- **A:** LLM colour, then the Foundry cloud evaluator, then Describer/Calm audio.
- **B:** more listening testers, then gamepad rumble.

## Two-person timeline

| Day | A (potencialbg) | B (Nikolay) | Handoff |
|---|---|---|---|
| Tue 20 | Stage 0 incl. scaffold with stubs for both lanes | `contracts/b/` v0 + sample; after the scaffold merges, set up locally | A → B: scaffold merged |
| Wed 21 | Stage 3 against the sample | Stage 1: real judge cut | **B → A: judge cut**; interfaces append-only from 18:00 |
| Thu 22 | Stage 3 on the real cut, TTS render, `build_bundle`, Bicep | Stage 2; `CrowdBus.duck` | **B → A: duck API** |
| Fri 23 | `commentary-track.ts`, **MVP live**, insurance video | Haptics, settings, UI; start `qa/` | MVP URL in README |
| Sat 24 | Stage 5; render `FRAGMENTS` in the evening | Stage 6; `FRAGMENTS` by 14:00; `qa/` done | **B → A: `qa/` + fragments** |
| Sun 25 | Stage 7 relay; live tests → `contracts/golden/a/`; 17:00 checkpoint | MCP server, eval questions, Stage 8 | **A → B: transcripts** |
| Mon 26 | Stage 9 from 13:00 | Listening test (morning), Stage 8 ends, video script + SRT | |
| Tue 27 | Edit, YouTube, **submit by 08:00 PT** | Final link, licence and secret checks | Submitted |

## Git workflow

- **Short branches, merged daily.** Name them `a/<topic>` or `b/<topic>`. A branch that lives a week means one huge merge on Mon 26, the worst possible day.
- Open a PR into `main` at least once a day. The other person reviews within about 2 h, then squash-merge.
- `main` must always run. CI needs no Azure credentials, and it discovers both lanes' tests by folder, so B's tests run without B touching `.github/`.
- Pull `main` before every stage prompt.

---

## Prompt for Nikolay's Claude (B)

Paste this at the start of every session. For a stage from `BUILD_PLAN.md`, paste this first and the stage prompt after it.

```text
I am Nikolay, Person B on Tely. My teammate potencialbg is Person A and owns everything Microsoft.
Read CLAUDE.md, TEAM_SPLIT.md (all of it) and BUILD_PLAN.md before anything else.
# WHY: TEAM_SPLIT.md says which files are mine. Another Claude (A's) is working in the same repo at the same time.
#      If we both only edit our own files, our PRs never conflict.

HARD RULES
1. Edit ONLY files listed under "B owns (Nikolay)" in TEAM_SPLIT.md, plus new files I create in my own folders.
   Before editing any file, check that it's on my list. If it isn't, don't edit it: add what I need under a
   "HANDOFF to A" heading in the PR description, and code against a stub of the same signature.
   # TIP: a stub with the right signature unblocks me today, and A replaces it without a merge conflict.
2. No Microsoft: never run az/azd, never call Azure, Foundry or Speech, never add azure-*, @azure/*,
   agent-framework or openai packages, and never create or read .env values. The Python and TS I write must run with no keys.
   # TIP: to see how the real Voice Live agent used my tools, read A's transcripts in contracts/golden/a/
   #      and turn them into regression tests in pipeline/tests/b/.
3. Before starting: git pull origin main, then work on a short branch b/<topic>. Open a PR at least once a day.
4. After Wed 21 18:00 Sofia my interface files (contracts/b/, web/src/contracts/b-exports.ts, the qa/__init__.py API)
   are append-only. Renaming or removing a field needs A's approval in the PR.
5. CLAUDE.md hard rules: synthetic data only, fictional clubs and players, no GPL, CC0 crowd clips only.

EXPLAIN AS YOU GO
- Before each step, write one line starting "TIP:" (how to do it well, or how to check it) or "WHY:" (the reason,
  citing the research file, e.g. "WHY: file 43 §2, Q&A tools may only see state at the playhead").
- In code, mark every place where my code meets A's with a comment: "# SEAM(B->A): <what crosses, which contract>".
- At the end, report: what runs now, what I verified, what is stubbed, the HANDOFF list, and which files I changed
  (all of them must be on my list).

MY WORK, IN ORDER
0. Today: contracts/b/ v0 as described in TEAM_SPLIT.md "The seams" point 1, a hand-written 90 s sample
   (pass chain, shot, save, goal) and a CDF validator test. Open the PR for A.
   # WHY: A's commentator starts on Wed against this sample.
   Touch pipeline/ and web/ only after A's Stage 0 scaffold has merged into main.
1. Stage 1 and Stage 2 (all of each), the Stage 4 pieces haptics.ts, settings.ts and the UI, and Stage 6 local-tools.ts
   and ask.ts. Use the prompts in BUILD_PLAN.md, with the paths from TEAM_SPLIT.md. Skip any step that calls Azure, deploys
   or edits A's files, and list it as a HANDOFF to A.
   # TIP: in Stage 2, segments.json gets NO cues field. A's commentary track loads the cue file itself (TEAM_SPLIT.md).
2. The Q&A brain in pipeline/tely/qa/, implementing exactly the API in TEAM_SPLIT.md "The seams" point 2:
   - the 8 tools from file 43 §3, ported from file 40's match_tools.py and clamped to playhead_s.
     Property test: across 200 random playheads, no evidence comes from after the playhead.
     # TIP: write this test first. The pitch says "0 spoiler leaks", so it's the most valuable test I own.
   - answer_text(): a keyword/intent router with no LLM. It is the offline fallback and the engine behind the preset questions.
   - PERSONA from file 40: Role, Tone, Tools, Scope; 1–2 sentences; never say what happens next; no betting advice.
   - catch_up(), hold_that_thought(), and FRAGMENTS (every fixed phrase A must render as audio).
   - mcp_server.py: the same tools on MCP SDK v2 MCPServer (file 18), streamable HTTP. MCP is an open protocol, not Microsoft.
   - contracts/golden/b/qa_cases.jsonl, which keeps the Python and TypeScript tools in step, and eval/qa_cases.jsonl with
     20+ questions, including "who scores next?", "who wins?" and off-topic ones, each with the expected behaviour.
3. Stage 8: radar, learn-the-sounds, Bluetooth calibration, Playwright + axe tests in web/tests/b/ (A wires them into CI),
   the listening-test kit, and running the test. Use TalkBack/VoiceOver; A does Narrator.
4. Stage 9: video script and shot list as drafts in docs/nikolay/ (A owns video/), SRT captions, listener footage (with consent),
   and link and licence checks.
Commit and push after each working piece.
```

## Prompt for A's Claude (potencialbg)

```text
I am potencialbg, Person A on Tely, and I own everything Microsoft. My teammate Nikolay is Person B.
Read CLAUDE.md, TEAM_SPLIT.md (all of it) and BUILD_PLAN.md before anything else.
# WHY: Nikolay's Claude works in the same repo at the same time. If each of us edits only our own files, PRs never conflict.

HARD RULES
1. Edit ONLY files listed under "A owns (potencialbg)" in TEAM_SPLIT.md, plus new files in my own folders.
   Anything else goes under a "HANDOFF to B" heading in the PR description.
   The one exception is Stage 0: today I create the scaffold, including stubs of B's files (TEAM_SPLIT.md "The cross-lane rules").
   After that PR merges, I never edit B's files again.
2. The relay imports B's package: from tely.qa import TOOL_SCHEMAS, PERSONA, call_tool, catch_up.
   Never copy or fork B's tools. The relay injects playhead_s from the session, and the model never sets the clock.
   # WHY: one implementation means the spoiler clamp B tests is exactly the code that runs live.
3. Azure Python packages go in pipeline/requirements-azure.txt, never in B's pyproject.toml. CI never installs them and never
   needs Azure credentials; tests mock the synthesiser and model.
4. After each live Voice Live test session, save contracts/golden/a/live_<date>.jsonl (question, tool calls with args,
   results, spoken answer, latency; no keys, tokens or audio) and tell Nikolay.
   # TIP: this is how B tests an agent whose model B can't run.
5. If git status shows B's generated files (events.jsonl, ticks.json.gz, signals.json, segments.json) as modified after
   build_bundle, don't commit them. That's a determinism bug: tell B.
6. git pull origin main before each stage, use short branches a/<topic>, and review B's PRs within about 2 h.
   Never print or commit keys. Follow the CLAUDE.md hard rules.

EXPLAIN AS YOU GO
- Before each step, write one "TIP:" or "WHY:" line for me, citing the research file.
- Mark every place where my code meets B's with "# SEAM(A->B): <what crosses, which contract>".
- At the end, report what runs, what I verified, what is stubbed, the HANDOFF list, and the files I changed.

MY WORK
Stage 0 (incl. scaffold with stubs for both lanes, CODEOWNERS from TEAM_SPLIT.md), Stage 3 (start on contracts/b/ sample),
Stage 4 (build_bundle WITHOUT merging cues into segments.json, web/src/lane-a/commentary-track.ts, Bicep, deploy),
Stage 5, Stage 6 answers.py (render B's FRAGMENTS), Stage 7 (relay, Voice Live, Container Apps, web/src/lane-a/live-ask.ts,
latency eval, .vscode/mcp.json, Copilot evidence), CI and uptime workflows, Stage 9 (README, SUBMISSION, edit, submit).
Commit and push after each working piece.
```

## Short reply for Nikolay

> Yes, with one twist. Voice Live does speech-to-text, the model and text-to-speech in one Microsoft service, so the live model stays with me (I'm keeping everything Microsoft). You own the agent's brain: the 8 tools clamped to the playhead, the persona prompt, a no-LLM router (also the offline fallback), catch-up, "hold that thought", the MCP server and the Q&A evals. All of it is pure Python/TS with no Microsoft SDKs or keys, and my relay imports your package. To balance the hours, you also take Stage 1 (generator + signals, so **you** define the event format), Stage 2 (sound stage), haptics/settings/UI, offline Ask, and accessibility plus the listening test. That's about 26.5 h for you and 29 h for me. **Every file has one owner**, so our two Claudes can run at the same time without conflicts. `TEAM_SPLIT.md` on `main` has the full file list and the prompt to paste into your Claude. First job today: `contracts/b/` with a 90 s sample match. Start on `pipeline/` and `web/` once my scaffold merges, about 30 min after I push it.
