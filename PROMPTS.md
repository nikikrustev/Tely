# Tely: every prompt to paste

**A = potencialbg** (owns all Microsoft work). **B = Nikolay** (no Microsoft).

## How to use this

1. Find your section: **A** or **B**.
2. For each session, open a **new** Claude Code session, run `git pull`, then copy **one** grey block and paste it. Each block is complete on its own, so you never need to combine two.
3. Before each step, check its **Wait for** line. If what it waits for isn't on `main` yet, do your next step that doesn't wait, or ask the other person.
4. After a step, do that stage's "You do this manually" list in `BUILD_PLAN.md`, if it has one.
5. When the PR is merged, tell the other person in chat.

**Order at a glance:**

| Day | A pastes | B pastes |
|---|---|---|
| Tue 20 | A1 | B1 (same time as A1). Then B2 once A1 is merged |
| Wed 21 | A2 | B2 (if not finished Tue) |
| Thu 22 | A3 | B3 |
| Fri 23 | A4 | B4 |
| Sat 24 | A5, then A6 in the evening | B5 (fragments by 14:00) |
| Sun 25 | A7 | B6 |
| Mon 26 | A8 (morning), A9 (from 13:00) | B7 (morning), B8 (from 13:00) |
| Tue 27 | A10 → submit by 08:00 PT | B9 |

**Handoffs between you** (tell the other person when your side is done):
- A1 merged → B can start B2.
- B1 merged → A can start A2.
- B2 merged → A switches to the real match in A3.
- B3 merged → A can finish A4.
- B5 merged → A can do A6 and A7.
- A7 transcripts pushed → B uses them in B6.

There's also a "fix-up" block at the end of each section, for when review comments or CI need a quick fix.

---

## A: potencialbg's prompts

### A1 · Tue 20 · Setup and scaffold
**Wait for:** nothing. Do the Stage 0 manual list in `BUILD_PLAN.md` alongside it (Azure account, budget, quota request).

```text
I am potencialbg (Person A, I own ALL Microsoft work). Nikolay (Person B) works in this repo at the same time.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "A owns" in TEAM_SPLIT.md (exception below for today);
anything I need from B goes under "HANDOFF to B" in the PR description. git pull main, work on branch a/<topic>, open a PR
when done. Never print or commit keys. CI must never need Azure keys.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets B's with
"# SEAM(A->B): ...". Finish by listing every file you changed and any HANDOFFs.

Task: Stage 0 of BUILD_PLAN.md (run its prompt), with these changes from TEAM_SPLIT.md:
- Today only, also create STUBS of B's files so B can start: pipeline/pyproject.toml (pytest with --import-mode=importlib),
  pipeline/tests/a/ and pipeline/tests/b/, web/ Vite + TS + vitest with web/tests/a/ and web/tests/b/, web/src/main.ts that
  calls mountLaneA() from web/src/lane-a/index.ts (a no-op for now), web/src/contracts/a-exports.ts and
  web/src/contracts/b-exports.ts with the interfaces from TEAM_SPLIT.md "The seams" point 3, and
  pipeline/tely/qa/__init__.py with the API from "The seams" point 2 (every function raises NotImplementedError).
- Azure Python packages go in pipeline/requirements-azure.txt, not pyproject.toml. CI installs pyproject only.
- CI must discover tests in both a/ and b/ folders without needing edits when new test files appear.
- Add .github/CODEOWNERS from TEAM_SPLIT.md "File ownership". Use @potencialbg for A, and ask me for Nikolay's GitHub username.
Push the scaffold as soon as it runs, because Nikolay is waiting on it.
```

### A2 · Wed 21 · Commentator on the sample
**Wait for:** B1 merged (`contracts/b/` with the 90 s sample).

```text
I am potencialbg (Person A, I own ALL Microsoft work). Nikolay (Person B) works in this repo at the same time.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "A owns" in TEAM_SPLIT.md; anything I need from B goes
under "HANDOFF to B" in the PR description. git pull main, work on branch a/<topic>, open a PR when done. Never print or
commit keys. CI must never need Azure keys.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets B's with
"# SEAM(A->B): ...". Finish by listing every file you changed and any HANDOFFs.

Task: Stage 3 of BUILD_PLAN.md (run its prompt), built against the hand-written sample in contracts/b/ because B's real
match generator isn't merged yet. Read the sample through one small loader function so switching to the real judge cut later
is a one-line change. Render the voice samples (python -m tely.voices) first and tell me where they are.
Tests go in pipeline/tests/a/ with the synthesiser mocked.
```

### A3 · Thu 22 · Commentator on the real match, bundle, infra
**Wait for:** B2 merged (real judge cut).

```text
I am potencialbg (Person A, I own ALL Microsoft work). Nikolay (Person B) works in this repo at the same time.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "A owns" in TEAM_SPLIT.md; anything I need from B goes
under "HANDOFF to B" in the PR description. git pull main, work on branch a/<topic>, open a PR when done. Never print or
commit keys. CI must never need Azure keys.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets B's with
"# SEAM(A->B): ...". Finish by listing every file you changed and any HANDOFFs.

Task:
1. Switch the Stage 3 commentary from the contracts/b/ sample to B's real judge cut
   (python -m tely.build_match --cut judge). Rebuild, re-check spoiler_leaks() == [] and truth_check 100%.
2. Write pipeline/tely/build_bundle.py from Stage 4 of BUILD_PLAN.md, with one change: do NOT merge cues into
   segments.json. My commentary track will load cues.en.radio.jsonl itself.
3. Write infra/main.bicep + azure.yaml for Static Web Apps Free (Stage 4) and web/staticwebapp.config.json. Don't deploy yet.
If git status shows B's generated files (events.jsonl, ticks.json.gz, signals.json, segments.json) as modified, don't commit
them; report it as a determinism bug for B.
```

### A4 · Fri 23 · MVP live
**Wait for:** B3 merged (crowd engine with `CrowdBus.duck`). Run `azd auth login` first.

```text
I am potencialbg (Person A, I own ALL Microsoft work). Nikolay (Person B) works in this repo at the same time.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "A owns" in TEAM_SPLIT.md; anything I need from B goes
under "HANDOFF to B" in the PR description. git pull main, work on branch a/<topic>, open a PR when done. Never print or
commit keys. CI must never need Azure keys.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets B's with
"# SEAM(A->B): ...". Finish by listing every file you changed and any HANDOFFs.

Task: my part of Stage 4 of BUILD_PLAN.md.
- web/src/lane-a/commentary-track.ts: load cues.en.radio.jsonl, decode each line ahead of time, play it at t_in on the
  AudioContext clock, duck the crowd through B's CrowdBus.duck()/unduck() (web/src/contracts/b-exports.ts), and export
  pause(), resume() and nextCueWithin(s) as declared in web/src/contracts/a-exports.ts.
- web/src/lane-a/index.ts: mountLaneA() starts the commentary track. B's main.ts already calls it.
- Show and speak the AI-voice + synthetic-data notice at Start (if the Start screen is B's file, put it in a HANDOFF to B).
- Tests in web/tests/a/: lines play at t_in ± 50 ms; ducking during every line.
- Build the bundle, npm run build, azd up. Open the URL and confirm only static requests. Put the URL at the top of README.md.
B owns haptics, settings and the UI, so don't build those.
```

### A5 · Sat 24 · Director agent on Foundry
**Wait for:** A4 deployed.
**First, in a terminal:** `git checkout main && git pull origin main`, then open the new session and paste the block.

```text
I am potencialbg (Person A, I own ALL Microsoft work). Nikolay (Person B) works in this repo at the same time.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "A owns" in TEAM_SPLIT.md; anything I need from B goes
under "HANDOFF to B" in the PR description. git pull main, work on branch a/<topic>, open a PR when done. Never print or
commit keys. CI must never need Azure keys.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets B's with
"# SEAM(A->B): ...". Finish by listing every file you changed and any HANDOFFs.

Task: Stage 5 of BUILD_PLAN.md (run its prompt). Tests in pipeline/tests/a/ with recorded fixtures (no Azure calls in CI).
Write my eval numbers to eval/report.json, and add eval/build_report.py, which merges eval/report.json, B's eval/qa.json and
B's eval/listening.json (if present) into eval/report.md. Redeploy with azd deploy.
If there's no model quota, use DIRECTOR=rules and note it in docs/DECISIONS.md.
```

### A6 · Sat 24 evening · Render the offline answers
**Wait for:** B5 merged (`FRAGMENTS` in `tely.qa`).

```text
I am potencialbg (Person A, I own ALL Microsoft work). Nikolay (Person B) works in this repo at the same time.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "A owns" in TEAM_SPLIT.md; anything I need from B goes
under "HANDOFF to B" in the PR description. git pull main, work on branch a/<topic>, open a PR when done. Never print or
commit keys. CI must never need Azure keys.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets B's with
"# SEAM(A->B): ...". Finish by listing every file you changed and any HANDOFFs.

Task: pipeline/tely/answers.py (Stage 6 of BUILD_PLAN.md, my part only). Import FRAGMENTS from tely.qa, render each
with the same voice and SSML-hash cache as the commentary, and write web/public/replay/v1/judge/answers/<sha>.mp3 plus
answers/index.json mapping fragment id -> audio file. Call it from build_bundle. Rebuild, azd deploy, and tell me the
fragment count and characters synthesised. B owns local-tools.ts and ask.ts, so don't touch them.
```

### A7 · Sun 25 · Live spoken questions (Voice Live)
**Wait for:** B5 merged (the `tely.qa` package is real, not stubs). Time box: 7 h. **Checkpoint 17:00:** if live Ask doesn't work on the deployed URL, leave it behind a flag that's off by default.

```text
I am potencialbg (Person A, I own ALL Microsoft work). Nikolay (Person B) works in this repo at the same time.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "A owns" in TEAM_SPLIT.md; anything I need from B goes
under "HANDOFF to B" in the PR description. git pull main, work on branch a/<topic>, open a PR when done. Never print or
commit keys. CI must never need Azure keys.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets B's with
"# SEAM(A->B): ...". Finish by listing every file you changed and any HANDOFFs.

Task: Stage 7 of BUILD_PLAN.md, with these changes from TEAM_SPLIT.md:
- relay/ IMPORTS B's tools: from tely.qa import TOOL_SCHEMAS, PERSONA, call_tool, catch_up. Don't write or copy
  tools.py or mcp_server.py; B owns those. The relay injects playhead_s from the session; the model never sets the clock.
- Host B's MCP server (tely.qa.mcp_server) in the same container at /mcp.
- Browser side goes in web/src/lane-a/live-ask.ts and registers with B's Ask button via Ask.registerLiveMode()
  (web/src/contracts/b-exports.ts). On any error or no answer within 8 s, fall back to B's preset menu.
- After each live test session, save contracts/golden/a/live_<date>.jsonl: question, tool calls with args, tool results,
  spoken answer and latency. No keys, tokens or audio.
- Latency p50/p95 goes into eval/report.json via eval/qa_latency.py.
Deploy with azd up and test from the deployed site.
```

### A8 · Mon 26 morning · CI, uptime, report
**Wait for:** B's Playwright tests merged (from B7). If they aren't there yet, do the rest and come back to this later.

```text
I am potencialbg (Person A, I own ALL Microsoft work). Nikolay (Person B) works in this repo at the same time.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "A owns" in TEAM_SPLIT.md; anything I need from B goes
under "HANDOFF to B" in the PR description. git pull main, work on branch a/<topic>, open a PR when done. Never print or
commit keys. CI must never need Azure keys.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets B's with
"# SEAM(A->B): ...". Finish by listing every file you changed and any HANDOFFs.

Task: my part of Stage 8 of BUILD_PLAN.md.
- Run B's Playwright + axe tests (web/tests/b/) in CI against a preview build, at 3 viewports.
- .github/workflows/uptime.yml: cron every 6 h fetching the deployed URL and manifest.json; badge in README.md.
- Run eval/build_report.py so eval/report.md includes B's qa.json and listening.json.
- If Describer/Calm won't happen, write "Radio only" in docs/DECISIONS.md.
Then I do the Windows Narrator walkthrough myself.
```

### A9 · Mon 26 from 13:00 · Video and write-up
**Wait for:** nothing (pinned time). Use B8's drafts in `docs/nikolay/` if they're there.

```text
I am potencialbg (Person A, I own ALL Microsoft work). Nikolay (Person B) works in this repo at the same time.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "A owns" in TEAM_SPLIT.md; anything I need from B goes
under "HANDOFF to B" in the PR description. git pull main, work on branch a/<topic>, open a PR when done. Never print or
commit keys.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Finish by listing every file you changed.

Task: Stage 9a of BUILD_PLAN.md (run its prompt). Start from Nikolay's drafts in docs/nikolay/ (video script, shot list,
captions) where they exist and move the final versions into video/. The README's team section names both of us, and
"How we built it" says honestly who built what. The pitch names only Microsoft tech we actually shipped.
```

### A10 · Tue 27 morning · Final checks, then submit
**Wait for:** the YouTube URL (you upload it). Submit by **08:00 PT (17:00 Sofia)**.

```text
I am potencialbg (Person A, I own ALL Microsoft work). Nikolay (Person B) works in this repo at the same time.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Never print or commit keys.
Explain as you go with one-line "TIP:" or "WHY:" notes. Finish by listing every file you changed.

Task: Stage 9b of BUILD_PLAN.md (run its prompt). The YouTube URL is: <paste URL>.
Include any issues Nikolay reported in his final-check PR (B9). For fixes in his files, list them for him rather than
editing them, unless he has already said he's done for the day.
```

### A · Fix-up (any time)

```text
I am potencialbg (Person A, I own ALL Microsoft work). Read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under
"A owns" in TEAM_SPLIT.md. Never print or commit keys.
Task: <describe the problem: failing CI check, review comment, or bug>. Fix it on a branch a/fix-<topic>, run the tests,
open a PR, and list the files you changed. If the fix belongs in Nikolay's files, don't edit them: write exactly what he
needs to change.
```

---

## B: Nikolay's prompts

### B1 · Tue 20 · Match data format and sample
**Wait for:** nothing. Paste it at the same time as A1.

```text
I am Nikolay (Person B, NO Microsoft in my work). potencialbg (Person A) works in this repo at the same time and owns all
Microsoft work.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "B owns" in TEAM_SPLIT.md; anything I need from A goes
under "HANDOFF to A" in the PR description, and I code against a stub instead. Never run az/azd, never call Azure, Foundry
or Speech, never add azure-*, @azure/*, agent-framework or openai packages, never touch .env. My code must run with no keys.
git pull main, work on branch b/<topic>, open a PR when done.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets A's with
"# SEAM(B->A): ...". Finish by listing every file you changed and any HANDOFFs.

Task: create contracts/b/, the match data format A's commentator will read (TEAM_SPLIT.md "The seams" point 1):
- events.jsonl format: CDF v0.3.2 event lines in the validated shape from stoynev research/26-cdf-spadl-data-tooling.md.
- meta.json (teams, fictional players, kits "Reds" and "Navy", kick-off, judge-cut window), signals.json (per-second
  win probability, suspense, tension, danger, crowd H/A; per-event xg, priority, spoken, spoken_past, zone),
  ticks.json.gz (ball 25 Hz, players at a rate you choose, at least 1 Hz).
- contracts/README.md explaining every field in plain words.
- A hand-written 90-second sample match using these formats: a pass chain, a shot, a save and a goal.
- A small test that checks the sample against the format (put it in contracts/b/ for now; it moves to pipeline/tests/b/ later).
Don't touch pipeline/ or web/ until A's scaffold is on main. Open the PR as soon as it's done, because A needs it on Wednesday.
```

### B2 · Tue 20 / Wed 21 · Synthetic match and signals
**Wait for:** A1 merged (scaffold).

```text
I am Nikolay (Person B, NO Microsoft in my work). potencialbg (Person A) works in this repo at the same time and owns all
Microsoft work.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "B owns" in TEAM_SPLIT.md; anything I need from A goes
under "HANDOFF to A" in the PR description, and I code against a stub instead. Never run az/azd, never call Azure, Foundry
or Speech, never add azure-*, @azure/*, agent-framework or openai packages, never touch .env. My code must run with no keys.
git pull main, work on branch b/<topic>, open a PR when done.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets A's with
"# SEAM(B->A): ...". Finish by listing every file you changed and any HANDOFFs.

Task: Stage 1 of BUILD_PLAN.md (run its prompt). Outputs must match the format in contracts/b/ exactly. If you need to add a
field, add it (don't rename or remove). Tests go in pipeline/tests/b/; move the contracts/b/ sample test there too.
The determinism test (identical sha256 on every run) matters extra for us: A's build reruns your generator, and any
difference shows up as a change to your files in A's commits.
Tell me when it's merged so I can tell A to switch from the sample to the real match.
```

### B3 · Thu 22 · Browser sound stage
**Wait for:** B2 merged. Download the CC0 crowd clips first (Stage 2 manual list in `BUILD_PLAN.md`).

```text
I am Nikolay (Person B, NO Microsoft in my work). potencialbg (Person A) works in this repo at the same time and owns all
Microsoft work.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "B owns" in TEAM_SPLIT.md; anything I need from A goes
under "HANDOFF to A" in the PR description, and I code against a stub instead. Never run az/azd, never call Azure, Foundry
or Speech, never add azure-*, @azure/*, agent-framework or openai packages, never touch .env. My code must run with no keys.
git pull main, work on branch b/<topic>, open a PR when done.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets A's with
"# SEAM(B->A): ...". Finish by listing every file you changed and any HANDOFFs.

Task: Stage 2 of BUILD_PLAN.md (run its prompt), with these changes from TEAM_SPLIT.md:
- segments.json has NO cues field. A's commentary track loads the cue file itself.
- The crowd engine implements CrowdBus.duck(db, rampMs) / unduck(rampMs) exactly as declared in
  web/src/contracts/b-exports.ts. A's commentary track calls it to duck the crowd under speech.
- Keep the call to mountLaneA() in main.ts.
- Tests go in web/tests/b/.
Tell me when CrowdBus.duck is merged, because A needs it on Friday.
```

### B4 · Fri 23 · Haptics, settings and UI
**Wait for:** B3 merged.

```text
I am Nikolay (Person B, NO Microsoft in my work). potencialbg (Person A) works in this repo at the same time and owns all
Microsoft work.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "B owns" in TEAM_SPLIT.md; anything I need from A goes
under "HANDOFF to A" in the PR description, and I code against a stub instead. Never run az/azd, never call Azure, Foundry
or Speech, never add azure-*, @azure/*, agent-framework or openai packages, never touch .env. My code must run with no keys.
git pull main, work on branch b/<topic>, open a PR when done.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets A's with
"# SEAM(B->A): ...". Finish by listing every file you changed and any HANDOFFs.

Task: my part of Stage 4 of BUILD_PLAN.md: web/src/haptics/haptics.ts, web/src/settings.ts and the UI (Start, Pause,
"Next big moment", Settings: all native buttons, at least 44 px, keyboard operable; aria-live for state changes only).
Pause and "Next big moment" must also pause and move A's commentary track through the functions in
web/src/contracts/a-exports.ts. Tests in web/tests/b/: every haptic pattern has at most 10 entries; settings survive a
localStorage that throws. A does the build_bundle, commentary track and deploy, so don't touch those.
If time is left, start pipeline/tely/qa/tools.py (next prompt, B5, part 1).
```

### B5 · Sat 24 · The Q&A brain and offline Ask
**Wait for:** nothing new. **Deadline: `FRAGMENTS` merged by 14:00**, so A can render the audio in the evening.

```text
I am Nikolay (Person B, NO Microsoft in my work). potencialbg (Person A) works in this repo at the same time and owns all
Microsoft work.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "B owns" in TEAM_SPLIT.md; anything I need from A goes
under "HANDOFF to A" in the PR description, and I code against a stub instead. Never run az/azd, never call Azure, Foundry
or Speech, never add azure-*, @azure/*, agent-framework or openai packages, never touch .env. My code must run with no keys.
git pull main, work on branch b/<topic>, open a PR when done.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets A's with
"# SEAM(B->A): ...". Finish by listing every file you changed and any HANDOFFs.

Task: the Q&A brain in pipeline/tely/qa/, implementing exactly the API in TEAM_SPLIT.md "The seams" point 2
(replace the NotImplementedError stubs; don't change the signatures, because A's relay imports them). In this order:
1. tools.py: the 8 tools from stoynev research/43-tely-architecture.md §3, ported from the match_tools.py code in
   40-conversational-commentator.md, every one clamped to playhead_s. Write this test FIRST: across 200 random playheads,
   no answer uses evidence from after the playhead.
2. fragments.py: FRAGMENTS, the list of every fixed phrase needing audio (Stage 6 of BUILD_PLAN.md: 18 zone clips,
   21 distance clips, one score/clock clip per minute of the cut, "hold that thought", "back to the action").
   Open a PR with this part alone by 14:00, because A renders the audio from it tonight.
3. router.py: answer_text(), a keyword/intent router with no LLM (the offline fallback and the preset engine).
4. persona.py: PERSONA from file 40 (Role, Tone, Tools, Scope; 1–2 sentences; never say what happens next; no betting).
5. catch_up() and hold_that_thought() (says THAT something is coming, never WHAT).
6. Stage 6 browser part: web/src/ask/local-tools.ts (TypeScript versions of the tools) and web/src/ask/ask.ts (big Ask
   button, preset questions, ducks the crowd and pauses A's commentary via a-exports.ts, plays the answer clips from
   answers/index.json, then "back to the action" + catch-up). Add Ask.registerLiveMode() from b-exports.ts so A can plug
   in the live voice mode later.
7. contracts/golden/b/qa_cases.jsonl ({tool, args, playhead_s, expected_say}) used by BOTH pytest and vitest, so the Python
   and TypeScript tools always say the same thing.
Tests in pipeline/tests/b/ and web/tests/b/.
```

### B6 · Sun 25 · MCP server, Q&A evals, Stage 8 start
**Wait for:** nothing. If A has pushed live transcripts to `contracts/golden/a/`, use them in step 3.

```text
I am Nikolay (Person B, NO Microsoft in my work). potencialbg (Person A) works in this repo at the same time and owns all
Microsoft work.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "B owns" in TEAM_SPLIT.md; anything I need from A goes
under "HANDOFF to A" in the PR description, and I code against a stub instead. Never run az/azd, never call Azure, Foundry
or Speech, never add azure-*, @azure/*, agent-framework or openai packages, never touch .env. My code must run with no keys.
git pull main, work on branch b/<topic>, open a PR when done.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets A's with
"# SEAM(B->A): ...". Finish by listing every file you changed and any HANDOFFs.

Task:
1. pipeline/tely/qa/mcp_server.py: the same tools on MCP SDK v2 MCPServer over streamable HTTP (research file 18).
   A hosts it in the relay container. Test that every tool clamps to the playhead.
2. eval/qa_cases.jsonl: at least 20 questions, including "who scores next?", "who wins?", off-topic ones and ambiguous player
   names, each with the expected behaviour. A script that runs them through answer_text() and writes eval/qa.json
   (spoiler leaks, % answered, % correct).
3. If contracts/golden/a/ has live transcripts from A, turn each tool call in them into a regression test in pipeline/tests/b/.
4. Stage 8 of BUILD_PLAN.md, items 1–3: sound radar (web/src/radar/), learn-the-sounds (web/src/learn/), Bluetooth calibration.
```

### B7 · Mon 26 morning · Accessibility tests and listening test
**Wait for:** nothing. Run the listening test with your 3+ people this morning.

```text
I am Nikolay (Person B, NO Microsoft in my work). potencialbg (Person A) works in this repo at the same time and owns all
Microsoft work.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "B owns" in TEAM_SPLIT.md; anything I need from A goes
under "HANDOFF to A" in the PR description, and I code against a stub instead. Never run az/azd, never call Azure, Foundry
or Speech, never add azure-*, @azure/*, agent-framework or openai packages, never touch .env. My code must run with no keys.
git pull main, work on branch b/<topic>, open a PR when done.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Mark code that meets A's with
"# SEAM(B->A): ...". Finish by listing every file you changed and any HANDOFFs.

Task: Stage 8 of BUILD_PLAN.md, items 4 and 6:
- Playwright + @axe-core/playwright tests in web/tests/b/ (3 viewports; wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa; reduced
  motion). Make them runnable locally with one npm script, and fix every violation in my files. A wires them into CI, so
  don't edit .github/; list violations in A's files as a HANDOFF.
- eval/listening_test.md (protocol from research file 36), eval/listening_test.csv, eval/score_listening.py, which writes
  eval/listening.json (not report.md; A's script merges it).
Remind me to get consent before quoting anyone or filming a reaction.
```

### B8 · Mon 26 from 13:00 · Video drafts
**Wait for:** nothing (pinned time).

```text
I am Nikolay (Person B, NO Microsoft in my work). potencialbg (Person A) works in this repo at the same time and owns all
Microsoft work.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "B owns" in TEAM_SPLIT.md. Never use Azure or any
Microsoft service. git pull main, work on branch b/<topic>, open a PR when done.
Explain as you go with one-line "TIP:" or "WHY:" notes (cite the research file). Finish by listing every file you changed.

Task: drafts for A's video, in docs/nikolay/video/ (A owns video/ and moves the final versions there):
- script.md: a 1:52 script, about 255 words, as a table (time, on screen, voiceover, burned caption), using the beats in
  Stage 9a of BUILD_PLAN.md and research files 14 and 42. Every number on screen must come from eval/report.json or a cited
  research file.
- shotlist.md: exactly what to record, with URLs and flags (?radar=1, which question to ask), in order.
- captions_sdh.srt for the match segment, built from the judge-cut cues, including sounds like [crowd rises].
- A list of the listener-reaction clips I filmed (with consent) and where they are.
```

### B9 · Tue 27 morning · Final checks (read-only report)
**Wait for:** A's README and SUBMISSION drafts on `main`.

```text
I am Nikolay (Person B, NO Microsoft in my work). Read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "B owns"
in TEAM_SPLIT.md. git pull main, work on branch b/final-checks.
Explain as you go with one-line "TIP:" or "WHY:" notes. Finish by listing every file you changed.

Task: final checks before A submits. Fix problems in my files; for A's files, only report them.
- Every link in README.md and SUBMISSION.md returns 200.
- assets/licences.json covers every file in web/public/crowd/, and all are CC0.
- No GPL dependency in web/ or pipeline/ (list licences from the lockfiles).
- Scan the repo and git history for key-like strings, .env contents, and real club, player or commentator names.
- Run all my tests (pytest pipeline/tests/b, vitest web/tests/b, Playwright + axe).
Write the findings into the PR description under "For A", most urgent first, and open the PR straight away.
```

### B · Fix-up (any time)

```text
I am Nikolay (Person B, NO Microsoft in my work). Read CLAUDE.md and TEAM_SPLIT.md first. Edit only files under "B owns"
in TEAM_SPLIT.md. Never use Azure or any Microsoft service.
Task: <describe the problem: failing CI check, review comment, or bug>. Fix it on a branch b/fix-<topic>, run the tests,
open a PR, and list the files you changed. If the fix belongs in A's files, don't edit them: write exactly what A needs to change.
```
