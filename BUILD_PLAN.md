# Audio Stands: build plan (one person, 20–27 Oct 2026)

_Written 20 Oct 2026. Based on the "Audio Stands — Idea Brief" and the day-by-day plan in `stoynev research/43-audio-stands-architecture.md`, cut down from two people to one._

_Weekdays are checked against the calendar. 20 Oct 2026 is a Tuesday. The brief and file 43 label the days one weekday off ("Tue 21 … Mon 27"); the dates there are right, only the weekday names are wrong._

**Deadline:** submissions close **Tue 27 Oct 23:59 PT**, which is **Wed 28 Oct 06:59 London / 08:59 Sofia** (file 12). **Target:** submit on **Tue 27 Oct by 08:00 PT (15:00 London / 17:00 Sofia)**. The brief's latest target is midday PT (19:00 London / 21:00 Sofia). The demo must stay up and free until **10 Nov**.

**Budget:** 7 working days × 8 h = 56 h (Wed 21 to Tue 27), plus about 2 h today for Stage 0.

## Timeline

| Day | Date | Hours | Stages | What runs at the end of the day |
|---|---|---|---|---|
| 0 | Tue 20 Oct (today) | ~2 | **Stage 0** setup | Smoke test plays an HD-voice MP3; you know whether you have model quota |
| 1 | Wed 21 | 8 | **Stage 1** (5 h), Stage 2 starts (3 h) | The judge-cut match data and a realism report; a crowd bed plays in the browser |
| 2 | Thu 22 | 8 | Stage 2 ends (3 h), **Stage 3** starts (5 h) | With your eyes closed, you hear the crowd swell and the ball rattle across the stereo field; the commentary script passes the spoiler test |
| 3 | Fri 23 | 8 | Stage 3 ends (2 h), **Stage 4** (6 h) | **MVP live on Static Web Apps:** the full judge cut with voice, crowd and haptics, needing no backend |
| | | | **━━━ CUT LINE ━━━** | **Stages 0–4 are already a complete entry you can submit.** Everything below adds score. |
| 4 | Sat 24 | 8 | **Stage 5** (4 h), **Stage 6** (4 h) | Director agent on Foundry with traces; the eval table; preset Ask works offline |
| 5 | Sun 25 | 8 | **Stage 7** (7 h) + 1 h buffer | A spoken question answered live in the commentator's voice |
| 6 | Mon 26 | 8 | **Stage 8** (4 h), **Stage 9** from 13:00 (4 h) | Accessibility CI green, listening test done, video footage recorded |
| 7 | Tue 27 | 8 | Stage 9 ends (6 h), 2 h buffer | **Submitted** |

Stage hours add up to 56: 5 + 6 + 7 + 6 + 4 + 4 + 7 + 4 + 10, plus 3 h of buffer.

### Cut line and checkpoints

**Never cut:** the replay on Static Web Apps, the look-ahead build-up, the crowd, the spoiler-leak measurement (target 0), the video, the write-up and the submission. **Stage 9 is pinned:** it starts on Mon 26 at 13:00 whatever state the build is in.

| Checkpoint | If this isn't true | Do this |
|---|---|---|
| End of Fri 23 | The MVP is deployed | Sat morning: finish Stage 4 before anything else. Drop Stage 7 now. |
| End of Sat 24 | Stages 5 and 6 are done | Sun: finish them, and drop Stage 7. |
| Sun 25, 17:00 | Live Ask works end to end on the deployed URL | Stop. Leave it behind a flag that defaults to off, and ship preset Ask. |
| Mon 26, 13:00 | (always) | Start Stage 9. |
| Tue 27, 08:00 PT | You have submitted | Submit what you have now. Whether you can still edit before the deadline is (unverified); check the form. |

**If you fall behind, drop in this order (first item first):**
1. Describer and Calm detail levels: ship Radio only (Stage 8, item 7).
2. LLM colour polish: templates only (Stage 5, optional item).
3. Live Voice Live questions (Stage 7). Keep preset Ask. This is a big loss for the Foundry category.
4. The Foundry cloud evaluator (Stage 5). Keep our code evals and the report.
5. The Director on a Foundry model: use the rules Director (Stage 5). This is a big loss for Agentic Design.
6. Offline preset Ask (Stage 6).

**Not in this plan (one person, 56 h).** Put these under "What's next" in the README and leave them out of the pitch:
- the live Event Hubs → Container Apps worker → Web PubSub path;
- Cosmos DB personalisation (settings stay in the browser);
- Bulgarian;
- game-controller rumble;
- "point your phone to listen" mode;
- native iPhone haptics (AHAP).

The brief's own cut list already drops most of these first.

## Before you start

- **One stage at a time, one fresh Claude Code session per stage.** Paste the stage's prompt, let it finish, then go through the "Done when" checks yourself before you start the next stage. Every prompt ends with a commit and push, so `main` always holds something that runs.
- **Hard rules (CLAUDE.md):**
  - synthetic data only;
  - no StatsBomb data, and no xT or EPV grids derived from real matches;
  - no Ultralytics and no GPL code, dependencies or build tools;
  - fictional clubs and players, CC0 crowd clips only, and every AI voice labelled as AI.
  - The no-GPL rule covers our code and build pipeline. For the video and testing tools you run by hand, this plan still picks non-GPL defaults: Clipchamp rather than OBS, Windows Narrator, TalkBack and VoiceOver.
- **Keys:** you enter keys and sign in yourself. Prompts use keyless auth (`az login` / managed identity) first, and fall back to keys only from a git-ignored `.env`. Claude Code never prints, logs or commits a key.
- **Numbers:** prices and limits come from files 43 and 44. Hours per stage are planning estimates. Minutes for manual tasks come from file 44's checklist where it gives them; the rest are my estimates.
- **Region:** Sweden Central (file 44), with Static Web Apps in `westeurope` (file 30; region list unverified). Category: **Best Use of Microsoft Foundry** (brief, file 42).

**Repo layout.** Every prompt assumes this:

```
pipeline/        Python 3.12 package `audiostands` (generator, interpret, commentary, agents, eval, bundle builder) + tests/
web/             Vite + TypeScript (vanilla, strict) client + vitest; replay bundle in web/public/replay/v1/judge/
relay/           Stage 7: FastAPI service (Voice Live relay + Stats tools + MCP server), Dockerfile
infra/           main.bicep (+ azure.yaml at the repo root), azd env "judge" in rg-as-judge
assets/          raw/ (git-ignored CC0 downloads), crowd_sources.csv, licences.json
eval/            report.md / report.json, listening test kit
video/           script, shot list, captions
scripts/         bootstrap_azure.sh, smoke_azure.py, prepare_crowd.py
docs/DECISIONS.md
```

---

## Stage 0: Accounts, quotas and scaffold

**Aim.** Start every sign-up and approval today, because quota approvals can take days (file 44). End with a repo skeleton, CI, and proof that Azure Speech and the Foundry model answer.

**Done when:**
- [ ] `python scripts/smoke_azure.py` prints PASS for Speech, and `out/smoke.mp3` plays the line in an en-US DragonHD voice.
- [ ] The model check prints PASS, or prints "model quota missing" and the quota request has been filed.
- [ ] `pytest` and `npm test` pass locally and in GitHub Actions.
- [ ] A $100 budget with alerts at 50% and 100% exists.

**Depends on:** nothing. **Time:** about 2 h today: 1.5 h of manual work and 0.5 h of Claude Code.

```text
Stage 0 of BUILD_PLAN.md: repo scaffold and Azure smoke test for Audio Stands.

Read first: CLAUDE.md; BUILD_PLAN.md ("Before you start", "Repo layout", Stage 0); in stoynev research/: 44-accounts-quotas-setup-checklist.md (day-1 checklist, bootstrap commands, budget), 46-copilot-github-azure-mcp-workflow.md (copilot-instructions draft, .vscode/mcp.json), 43-audio-stands-architecture.md (TL;DR and §7: HD voices are real-time only and en-US DragonHD only).

Create:
- .gitignore: .env, out/, node_modules/, assets/raw/, __pycache__/, .azure/, dist/.
- .env.example (no real values): FOUNDRY_RESOURCE, FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_MODEL=gpt-5.4-mini, SPEECH_REGION=swedencentral, SPEECH_ENDPOINT, SPEECH_KEY (optional, only if keyless auth fails), TTS_VOICE=en-US-Andrew:DragonHDLatestNeural.
- pipeline/pyproject.toml (package audiostands, Python 3.12, pytest), pipeline/audiostands/__init__.py, pipeline/tests/test_smoke.py.
- web/: Vite + TypeScript (vanilla, strict) + vitest, with one passing test.
- .github/workflows/ci.yml: pytest + vitest on every push and PR. CI must never need Azure credentials.
- .github/copilot-instructions.md: file 46's draft, updated to this repo layout and to the one-person scope.
- .vscode/mcp.json: Azure MCP Server with --read-only (file 46).
- scripts/bootstrap_azure.sh: file 44's bootstrap for rg-as-dev and rg-as-judge in swedencentral (register providers, create the groups, an AIServices S0 resource with a custom domain, usage list, quota tiers, a gpt-5.4-mini GlobalStandard deployment with capacity 10 and NoAutoUpgrade). Do NOT create Cosmos DB, Web PubSub or Event Hubs; this plan doesn't use them. Check each flag with --help and mark doubtful ones "(unverified)" in comments. Don't run it: I run it myself after az login.
- scripts/smoke_azure.py:
  (1) synthesise "Audio Stands smoke test. The Reds are breaking down the far side." with TTS_VOICE to out/smoke.mp3 using the Speech SDK, keyless with DefaultAzureCredential first and SPEECH_KEY from .env as a fallback;
  (2) one short chat call to FOUNDRY_MODEL.
  Print PASS/FAIL per check. On a quota or deployment error, print "model quota missing: Director falls back to rules (Stage 5)" instead of crashing. Never print, log or commit keys or tokens.
- docs/DECISIONS.md: one-person scope, the "Not in this plan" list from BUILD_PLAN.md, region Sweden Central, category Best Use of Microsoft Foundry, hard rules from CLAUDE.md.

Then run pytest, npm test and scripts/smoke_azure.py. If .env or az login isn't ready, report exactly what is missing and skip only that check. Don't try to sign in or create Azure resources. Confirm that out/smoke.mp3 exists and is larger than 1 KB.
Run it, verify it, commit and push.
```

**You do this manually:**
- [ ] **(5 min, do first)** Check that you are registered and listed on project 126726 in Innovation Studio. Registration closed on 20 Oct at 12:00 PT (file 12). If you aren't registered, sort that out before anything else. While you are there, note which fields the submission form has (file 12's open questions): 10 min.
- [ ] **(5 min) [CARD] [PHONE]** Create an Azure free account (file 44, step 1).
- [ ] **(2 min)** Upgrade to Pay-As-You-Go straight away. Unused credit stays for its 30 days. Note the expiry date (file 44, step 2).
- [ ] **(3 min)** Create a $100 budget with alerts at 50% and 100% (file 44, step 3). Budgets don't stop spending (file 21).
- [ ] **(10 min)** Run `az login`, then `bash scripts/bootstrap_azure.sh`. Alternatively, create the Foundry resource and project in the portal (file 44, steps 4–5 and 7).
- [ ] **(5 min, the day-1 risk)** Check quota in Foundry → Quota. **If `gpt-5.4-mini` shows 0 TPM, file https://aka.ms/oai/stuquotarequest now** (15 min). File 44 says approval takes "days, approval not guaranteed". Stages 1–4 don't need it.
- [ ] **(5 min)** Smoke-test Voice Live in the Foundry playground with `gpt-realtime-2.1-mini` and an **en-US** HD voice. File 43 corrects file 44: the en-GB HD names may not exist.
- [ ] **(3 min)** Copy `.env.example` to `.env` and fill in the endpoints. Add `SPEECH_KEY` only if keyless auth fails.
- [ ] **(5 min)** Make sure `github.com/nikikrustev/BerbataAI` is public, or that its owner will make it public before you submit (file 12). Decide whether you're happy for the research notes, including the competitor intel file, to be public alongside the code.
- [ ] **(10 min)** Turn on Copilot Free in VS Code, install the Azure MCP Server extension and Node LTS, then run one Agent Mode prompt that lists `rg-as-dev` (file 44, step 13).
- [ ] **(2 min)** Create or choose a YouTube channel. Don't upload anything yet.
- [ ] **(3 min)** Create a free Freesound account; Stage 2 needs it to download crowd clips.
- [ ] **(15 min)** Book at least 3 people for a 20-minute eyes-closed listening test on Mon 26 morning. If you want, also email RNIB or a local blind or low-vision group. File 36 explains how to word it, and says to name an organisation in the write-up only if you really contacted it.
- [ ] **(2 min)** Decide on the product name; "Audio Stands" is the default.

---

## Stage 1: Seeded synthetic match and Interpret signals

**Aim.** Generate one reproducible synthetic match. From it, pick an 8-minute "judge cut" and compute the signals everything else reads: win probability, suspense, danger, tension, crowd state and haptic cues.

**Done when:**
- [ ] `python -m audiostands.build_match --cut judge` writes `events.jsonl`, `ticks.json.gz` and `signals.json` to `web/public/replay/v1/judge/` in under 60 s.
- [ ] Two runs give identical sha256 for every file.
- [ ] The judge cut contains at least 1 goal, 1 save, 1 card, 1 VAR-style check and 4 shots (stored in `pipeline/judge_cut.json`).
- [ ] `pytest` passes, including:
  - **crowd outcome-invariance:** flipping every shot's outcome leaves the crowd values before each shot unchanged;
  - **look-ahead swell:** at the moment of every shot with xG ≥ 0.1, home excitement is at least 0.2 higher than it was 8 s earlier (our test threshold).
- [ ] `out/realism_report.md` lists goals, passes, shots and distance against the targets cited in files 02 and 19, marked green or red.

**Depends on:** Stage 0 (scaffold). **Time:** 5 h.

```text
Stage 1 of BUILD_PLAN.md: seeded synthetic match + Interpret signals for the judge cut.

Read first: CLAUDE.md; BUILD_PLAN.md Stage 1; in stoynev research/: 43-audio-stands-architecture.md §2–§3 and §6 (clock, spoiler firewall, cue contract, judge cut), 02-synthetic-match-data.md (generator) together with the two fixes in 33-synthetic-possession-value.md ("Fixes to file 02 generate()"), 19-realistic-player-movement.md (Movement model), 23-win-probability-and-momentum.md (Poisson win probability), 39-anticipatory-emotional-commentary.md (suspense/surprise code, LEAD_S), 38-reactive-crowd-atmosphere.md (crowd_states with spoiler-safe look-ahead), 41-haptics-match-tension.md (tacton vocabulary), 09-pressure-pressing-ppda.md (Andrienko pressure, optional input to tension), 26-cdf-spadl-data-tooling.md (CDF field names only).

Build in pipeline/audiostands/:
- generator.py: the file 02 possession-chain generator with both file 33 fixes, plus synthetic keeper saves, yellow/red cards and a "var_check" event (a stoppage of about 20 s that ends in a decision). Fictional clubs only: home "Reds" (red shirts, white shorts), away "Navy" (navy, sky-blue sleeves). Player names are generated from the seed; no real people, clubs or chants.
- movement.py: the file 19 Movement model → 22 players at 25 Hz, plus the ball track from events.
- clock.py: Clock, director_window, qa_view and release from file 43, with D_S = 10 and PREFETCH_S = 3.
- interpret.py: per-second win probability (file 23), suspense/surprise (file 39), shot xG from the generator, danger per team from ball zone and possession (our formula, labelled "Berbata definition" in a docstring), tension 0–1 for the heartbeat.
- crowd.py: file 38 crowd_states → H and A {excitement, valence, danger} at 1 Hz plus one-shots (goal roar, groan, hush for var_check). Look-ahead may use chance quality only, never the outcome.
- haptics.py: haptic cues {tacton, team, t} from file 41's vocabulary.
- judge_cut.py: scan seeds 1–500 (stop at the first hit) for an 8-minute window with ≥ 1 goal, ≥ 1 save, ≥ 1 card, 1 var_check and ≥ 4 shots; write {seed, t_start, t_end} to pipeline/judge_cut.json.
- build_match.py (python -m audiostands.build_match --cut judge): writes web/public/replay/v1/judge/events.jsonl, ticks.json.gz (ball 25 Hz; crowd H/A and tension 1 Hz) and signals.json, plus out/realism_report.md over 50 seeds against the targets cited in files 02 and 19 (green/red per row; don't invent thresholds).
- tests (pytest):
  - determinism: two runs → identical sha256 for every output;
  - regression tests for both file 33 bugs;
  - crowd outcome-invariance: flip every shot outcome, and crowd values before each shot's time stay identical;
  - look-ahead swell: for every shot with xG ≥ 0.1, H.excitement at the shot time is ≥ 0.2 above its value 8 s earlier (our threshold: if it fails, tune the crowd weights, not the test);
  - valence has opposite signs for H and A after a goal.

No real match data anywhere, no xT/EPV grids from real matches, no GPL dependencies (numpy/scipy are fine). build_match must finish in under 60 s on a laptop.
Run it, verify it, commit and push.
```

**You do this manually:**
- [ ] **(15 min)** Read `out/realism_report.md`. Red rows are fine; they go into the README honestly (file 19 already lists which gaps to expect).
- [ ] **(10 min)** Skim the judge-cut events: does the 8-minute story make sense to tell (chance, save, card, goal, VAR hush)? If not, ask Claude Code for the next seed that qualifies.

---

## Stage 2: The browser sound stage (crowd, ball, earcons)

**Aim.** Hear the match without any commentary yet. A spatial crowd bed reacts to the match, and a rattling ball moves across the stereo field from the halfway seat.

**Done when:**
- [ ] `npm test` passes, including a scheduler test over the real judge-cut segments. It checks that by 1 s after every shot, the crowd bus gain is above its level 8 s before the shot: the crowd swells within 1 s of a synthetic shot event.
- [ ] `npm run dev`, then Start (mouse or Enter): the crowd is audible within 1 s.
- [ ] `?debug=1` shows the crowd gain, ball x and playhead moving.
- [ ] With your eyes closed and headphones on, you can say which half the ball is in at 4 of 5 random moments.
- [ ] `assets/licences.json` lists every clip, and all of them are CC0.

**Depends on:** Stage 1. **Time:** 6 h, including about 1.7 h of manual work.

```text
Stage 2 of BUILD_PLAN.md: the browser sound stage (crowd + ball + earcons) playing the judge-cut ticks.

Read first: CLAUDE.md; BUILD_PLAN.md Stage 2; in stoynev research/: 37-spatial-audio-in-the-browser.md (audio-stands.ts, halfway seat default, Firefox AudioListener quirk, synthetic stadium IR, earcon spacing ≥ 300 ms, Bluetooth latency), 38-reactive-crowd-atmosphere.md (CrowdEngine, §4 CC0 clip list and audit rule, §6 granular bed and two-clocks scheduling, +12 dB speech rule), 32-accessible-responsive-viewer.md (player markup with live regions, Announcer), 43-audio-stands-architecture.md §6 (ReplaySource, wire(), segments).

Build:
- pipeline/audiostands/build_segments.py: ticks.json.gz → web/public/replay/v1/judge/segments.json (2 s segments; ball at 10 Hz; crowd H/A; tension; cues: [] for now).
- scripts/prepare_crowd.py: read assets/raw/* and assets/crowd_sources.csv (id, file, author, url, licence, role), trim and loudness-normalise to web/public/crowd/<role>_<n>.mp3 using an LGPL build of ffmpeg, and write assets/licences.json. Refuse any row whose licence isn't CC0. If assets/raw is empty, generate placeholder noise beds so everything still runs, and print a warning.
- web/src/audio/audio-stands.ts (file 37): halfway seat by default; the ball is a broadband rattling texture on an HRTF PannerNode; procedural thud/whistle/net auditory icons ≥ 300 ms apart; Firefox setPosition/setOrientation fallback.
- web/src/audio/stadium-ir.ts: a generated stadium impulse response (no downloaded IRs).
- web/src/audio/crowd-engine.ts (file 38): looped/granular beds, one-shots with refractory limits, safety limiter, a speech-ducking bus input for later.
- web/src/replay/replay-source.ts and web/src/wire.ts (file 43).
- web/index.html + web/src/main.ts: one large native "Start" button (unlocks audio), polite and assertive live regions present from page load, a ?debug=1 panel with crowd gain, ball x and playhead.
- vitest:
  - ball x → panner position mapping;
  - crowd excitement → bus gain is monotonic;
  - the refractory limit blocks repeated one-shots;
  - a scheduler test that runs CrowdEngine over the real segments.json with a mocked AudioContext and asserts that, by 1 s after every shot time in events.jsonl, the crowd bus gain is above its level 8 s before that shot.

Run npm test and npm run build, start the dev server, and confirm in the browser that Start plays audio and the debug panel moves.
Run it, verify it, commit and push.
```

**You do this manually:**
- [ ] **(45 min)** Log in to Freesound and download about 15 CC0 clips from file 38 §4 (St Pauli pack, felix.blume groan, Krizin cheers, ShangusBurger walla, CHallSmith reactions) into `assets/raw/`. **Listen to every clip** and cut any sung chant, club name or abuse (file 38's audit rule).
- [ ] **(10 min)** Fill in `assets/crowd_sources.csv` (id, file, author, URL, licence, role). Then run `python scripts/prepare_crowd.py`.
- [ ] **(45 min)** Tune by ear with headphones, eyes closed, at least two full passes of the judge cut. Is the bed too loud? Do one-shots repeat too often? Is the ball easy to follow? Give Claude Code your notes as concrete changes ("goal roar 3 dB quieter, refractory 20 s").

---

## Stage 3: Look-ahead commentary and the HD voice

**Aim.** A Radio-level commentary script. It builds about 4 s before each big chance using chance quality only, calls the moment after it happens, and is verified for numbers and spoilers. Every line is pre-rendered once in an Azure HD voice.

**Done when:**
- [ ] `python -m audiostands.build_commentary --cut judge` writes `cues.en.radio.jsonl`, MP3s by SSML hash, `captions_sdh.vtt` and `descriptions.vtt`.
- [ ] In CI, `spoiler_leaks()` returns `[]` (target 0) and `truth_check` passes 100%.
- [ ] Every build line starts LEAD_S ± 0.5 s before its shot.
- [ ] A second build makes 0 TTS calls (cache by SSML hash).
- [ ] You picked a voice by ear from `out/voices/`.

**Depends on:** Stage 1, and Stage 0 (Speech). **Time:** 7 h.

```text
Stage 3 of BUILD_PLAN.md: look-ahead commentary (templates), verifier, spoiler-leak test and pre-rendered HD voice.

Read first: CLAUDE.md; BUILD_PLAN.md Stage 3; in stoynev research/: 39-anticipatory-emotional-commentary.md (look-ahead planner, reveal policy, LEAD_S = 4 s, SSML builders, pre-synthesis cache), 22-explanation-generation-patterns.md (templates, wordalization, verifier), 36-blind-fans-and-audio-description.md (ball-first grammar, Radio level, design rules 1–8), 27-voice-speech-and-audio.md together with the correction box in 40-conversational-commentator.md (en-US DragonHD voices only; DragonHD has [style] tags and <break> but no <prosody>/express-as; HD is real-time only, no batch), 43-audio-stands-architecture.md §2–§3 (firewall table, 6 s budget, cue contract, spoiler_leaks code).

Build in pipeline/audiostands/commentary/:
- templates.py: Radio-level, ball-first lines ("Final third, far side, Reds… Okafor!"); both kits and the direction of play at kick-off; the scorer named only after the play is described; a state line at least every 20 s; "ball's out" before any background. Varied phrasings, chosen by seed.
- planner.py: the file 39 planner over the window [P, P+D]. Build lines at shot − LEAD_S use chance quality only; calls at shot + 0.2 s; priority, stale drop and quiet fill. Emit cues in the file 43 contract (cue_id, kind, reveal, tc_in, t_in, text.radio, utterance, crowd_state, haptic, spatial, evidence, truth_check, spoiler_check, source).
- verifier.py: truth_check (every number and name in a line matches events/signals) and spoiler_check (no outcome word in any line timed before its event).
- spoiler.py: spoiler_leaks() from file 43 and "spoiler lift" from file 39, as functions and a CLI report.
- ssml.py + tts.py: DragonHD SSML with [style] bands calm → curious → urgent → excited → shouting and a low temperature. Pre-synthesise MP3 with the Speech SDK, cached by SSML sha256, with 429 retry and backoff. Never re-synthesise an existing hash. Keyless first, SPEECH_KEY fallback; never log keys.
- build_commentary.py (python -m audiostands.build_commentary --cut judge): writes cues.en.radio.jsonl, audio/en/radio/<sha>.mp3 (real durations written back into the cues), captions_sdh.vtt and descriptions.vtt (code from files 32/42) into web/public/replay/v1/judge/. Report the line count and characters synthesised.
- voices.py (python -m audiostands.voices): render the same 4 lines (build-up, goal call, miss, calm state line) in 3 en-US DragonHD voices to out/voices/.
- tests (all run in CI with the synthesiser mocked; CI must not call Azure):
  - spoiler_leaks == [];
  - truth_check 100% pass;
  - each build line's t_in is LEAD_S ± 0.5 s before its shot;
  - no two lines overlap;
  - a second build makes 0 TTS calls.

Render the voice samples first. If TTS_VOICE in .env is still the default, build with it and tell me where the samples are, so I can switch later (the cache makes a re-render cheap).
Run it, verify it, commit and push.
```

**You do this manually:**
- [ ] **(20 min)** Listen to `out/voices/`, pick the voice whose build-up and goal call sound most like a commentator, and set `TTS_VOICE` in `.env`.
- [ ] **(30 min)** Read `cues.en.radio.jsonl` aloud, or play the MP3s in order. Is it ball-first? Are there too many state lines? Is the tone right? Send fixes to Claude Code as template changes.
- [ ] **(5 min)** Check Speech usage in the portal. File 43 estimates about $1.46 for a full 95-minute HD track; the 8-minute cut is a small fraction of that.

---

## Stage 4: Replay MVP, deployed (zero backend)

**Aim.** The full judge-cut experience at a public URL, on static files only: commentary on the audio clock with ducking, crowd, ball, haptics, club end and mix. After this stage you have a submittable entry.

**Done when:**
- [ ] The Static Web Apps URL opens in a private window. Start plays the 8-minute cut:
  - the voice lifts about 4 s before each big chance;
  - there is a goal call and a roar from your end;
  - switching to Navy turns the goal into a hush.
- [ ] The browser network panel shows only static file requests.
- [ ] On Android Chrome the heartbeat and goal tacton vibrate. iPhone shows the honest "audio only" message.
- [ ] vitest passes: lines play at `t_in` ± 50 ms on the audio clock, and the crowd ducks during every line.
- [ ] The URL is at the top of `README.md`, and a rough 60–90 s insurance video is saved.

**Depends on:** Stages 2 and 3. **Time:** 6 h.

```text
Stage 4 of BUILD_PLAN.md: the playable judge-cut replay, deployed to Azure Static Web Apps with zero backend. This is the MVP.

Read first: CLAUDE.md; BUILD_PLAN.md Stage 4; in stoynev research/: 43-audio-stands-architecture.md §6 (bundle layout, manifest, ReplaySource, wire) and §7 (Bluetooth and iOS risks), 41-haptics-match-tension.md (haptics.ts, tacton vocabulary, honest iOS line, wake lock, "did you feel it?" button), 27-voice-speech-and-audio.md (crowd ducking snippet), 38-reactive-crowd-atmosphere.md (+12 dB commentary over crowd, mirrored club end), 32-accessible-responsive-viewer.md (live regions, throttled Announcer), 21-demo-uptime-cost-and-ops.md (replay mode, staticwebapp.config.json), 30-infra-as-code-azd-bicep.md (azure.yaml + Bicep pattern; swaLocation westeurope (unverified)).

Build:
- pipeline/audiostands/build_bundle.py (python -m audiostands.build_bundle --cut judge): run build_match, build_commentary and build_segments in order; merge cues into segments.json; write manifest.json in the file 43 shape (delay_s, kits, chapters for "next big moment", tracks, ai_voice_notice "Commentary uses Azure AI voices. Match data is synthetic.", sha256 of every file). Fail if the bundle exceeds 200 MB.
- web/src/audio/commentary-track.ts: fetch and decode each line ahead of time, play it at its t_in on the AudioContext clock, and duck the crowd at least 12 dB under speech with soft ramps.
- web/src/haptics/haptics.ts (file 41): heartbeat tempo from tension, event tactons, home/away signatures, firing at audibleAt − 20 ms using outputLatency. Honest message on iPhone and Firefox Android, a "did you feel it?" test button, Screen Wake Lock.
- web/src/settings.ts: club end (Reds/Navy, flips crowd valence), crowd/voice mix slider, haptics off / key moments / full. Store in localStorage inside try/catch; everything works without storage.
- UI: Start, Pause, "Next big moment" (chapter skip) and Settings. All native buttons, at least 44 px, fully keyboard operable. While audio plays, aria-live announces state changes only (score, half time), not every cue. The AI-voice and synthetic-data notice is visible and spoken at the start.
- infra/main.bicep + azure.yaml: Static Web Apps Free only, azd env "judge", resource group rg-as-judge. web/staticwebapp.config.json with MIME types for .jsonl/.gz/.mp3 and long cache headers for hashed audio.
- vitest:
  - commentary lines are scheduled at t_in ± 50 ms on the audio clock;
  - ducking is applied during every line;
  - every haptic pattern has ≤ 10 entries;
  - settings survive a localStorage that throws.

Build the bundle, run npm run build, then deploy with azd up (I'm logged in with azd auth login; if not, stop and tell me). Open the deployed URL and confirm the network panel shows only static file requests. Put the URL at the top of README.md.
Run it, verify it, commit and push.
```

**You do this manually:**
- [ ] **(2 min)** Run `azd auth login` before you paste the prompt.
- [ ] **(20 min)** Listen to the whole 8-minute cut on the deployed URL with headphones, eyes closed. Write down the 3 worst moments and fix those first, today or on Saturday.
- [ ] **(10 min)** On an Android phone in Chrome (if you have one), press "did you feel it?", then feel the heartbeat rise and the goal pattern.
- [ ] **(10 min)** On an iPhone in Safari: is the audio fine, and does the "audio only" message appear?
- [ ] **(30 min) Insurance video.** Record 60–90 s of the deployed MVP with system audio, using Clipchamp's screen recorder or the Windows Snipping Tool recorder (check that it captures system audio (unverified)). If everything after this goes wrong, this video plus the README is still an entry.

---

## Stage 5: Director agent on Foundry, tracing and the eval table

**Aim.** Make the "agent that hears the next 10 seconds" real. An Agent Framework Director on a Foundry model reads the look-ahead window and outputs only a tension plan. A Verifier in code checks it, and a rules Director takes over on any failure. Traces and a measured eval table back the Agentic Design and Foundry claims.

**Done when:**
- [ ] `DIRECTOR=foundry python -m audiostands.build_bundle --cut judge` runs through the Agent Framework workflow, and the traces appear in Application Insights / Foundry.
- [ ] `spoiler_leaks()` is still `[]`.
- [ ] `eval/report.md` shows:
  - spoiler leaks (0), spoiler lift, % numbers verified, % template fallback;
  - Director calls and fallbacks;
  - plan→verify→TTS latency p50/p95 for build lines against the 6 s budget.
- [ ] The redeployed site uses the Director's plans.

**Depends on:** Stage 4, and model quota from Stage 0. Without quota, run `DIRECTOR=rules` and say so in the README. **Time:** 4 h.

```text
Stage 5 of BUILD_PLAN.md: the Director agent on Microsoft Foundry (Agent Framework), tracing, and the evaluation table.

Read first: CLAUDE.md; BUILD_PLAN.md Stage 5; in stoynev research/: 18-agentic-design-for-pipelines.md (Agent Framework 1.22 workflows, FoundryChatClient, tracing with configure_azure_monitor + enable_instrumentation, Foundry code-based custom evaluator and its sandbox limits), 03-foundry-llm-explain.md (Foundry project endpoint), 43-audio-stands-architecture.md §1–§2 (Director inputs/outputs, firewall table, at most one call per 10 s, ≤ 1,200 tokens per call, 10K TPM ceiling), 39-anticipatory-emotional-commentary.md (reveal policy, spoiler lift), 42-audio-competitors-and-demo.md (information-asymmetry framing), 22-explanation-generation-patterns.md (locked-placeholder polish, optional).

Build:
- pipeline/audiostands/agents/director.py: an Agent Framework agent on FOUNDRY_MODEL. Input: the window [P, P+D] as compact features (event types, xG, zone, seconds to the next shot). Output, validated against a JSON schema: {build_up_level 0–1, lead_s, hold_ms, hint_type ∈ danger|counter|set_piece|none}. Its instructions forbid outcome information, and the Verifier rejects any field outside the schema.
- pipeline/audiostands/agents/rules_director.py: the same output from file 39's rules. Select with DIRECTOR=foundry|rules. If a model call fails (no quota, 429, timeout), that window falls back to rules and the fallback is recorded.
- pipeline/audiostands/agents/workflow.py: an Agent Framework workflow Director → Commentator (templates) → Verifier (code) → TTS executor, with at most one Director call per 10 s of match time. OpenTelemetry tracing to Application Insights: add a workspace-based App Insights (dailyQuotaGb 1) to infra/main.bicep, pass its connection details through the azd env, and keep keys out of files.
- pipeline/audiostands/eval/:
  (a) spoiler leaks (target 0), spoiler lift, % numbers verified, % template fallback, Director calls and fallbacks;
  (b) a --realtime harness that plays the cut at wall-clock speed and logs, for each build line, plan → verify → TTS latency against the 6 s budget (p50/p95);
  (c) a Foundry code-based custom evaluator for numeric truth (file 18), uploaded and run once if the SDK supports it; otherwise run the same grader locally and say so.
  Write eval/report.md and eval/report.json.
- Switch build_bundle to the workflow, rebuild the bundle and redeploy with azd deploy.
- Optional, only if less than 3 h of this stage has been used: LLM colour lines with locked placeholders and stale drop (file 22). Otherwise skip, and note it in docs/DECISIONS.md.
- tests: Director output schema; rules fallback on a simulated 429; spoiler_leaks still [] with DIRECTOR=foundry, using recorded fixtures (CI makes no Azure calls).

Run it, verify it, commit and push.
```

**You do this manually:**
- [ ] **(5 min)** Check that the `gpt-5.4-mini` deployment exists and has quota. If not, use `DIRECTOR=rules` and move on. Don't wait for approval.
- [ ] **(15 min)** Open the traces in Foundry (Build → Agents → Traces, per file 18) or App Insights, and take two screenshots for the README and the video.
- [ ] **(20 min)** Do an A/B listen of the cut with the rules Director and the Foundry Director. Keep the better one, and record which one in `docs/DECISIONS.md`.

---

## Stage 6: Ask the commentator, offline presets

**Aim.** Make the big Ask button work with no backend. A fan picks a preset question ("Where's the ball?", "What's the score?", "What did I miss?"). The crowd dips and the commentator's voice answers from data up to the playhead, then catches the fan up.

**Done when:**
- [ ] On the deployed URL, mid-attack, Ask → "Where's the ball?" plays a zone answer and a ball ping. Then comes "back to the action" with a one-line catch-up.
- [ ] If a build-up line is due within 4 s, the fan hears "hold that thought" first.
- [ ] The vitest property test passes: across 200 random playheads, no answer uses an event after the playhead.
- [ ] The Ask button works by keyboard, and in Windows Narrator by activating it once.

**Depends on:** Stage 4. **Time:** 4 h.

```text
Stage 6 of BUILD_PLAN.md: "Ask the commentator" with preset questions that work offline in the replay.

Read first: CLAUDE.md; BUILD_PLAN.md Stage 6; in stoynev research/: 40-conversational-commentator.md (§1 toggle Ask button and VoiceOver/TalkBack gestures, tool definitions, catch-up, ducking), 43-audio-stands-architecture.md §3 (tool schemas, {say, evidence_ids, as_of_clock}) and §6 (offline Ask, clip counts), 36-blind-fans-and-audio-description.md (rules 4 and 7: short answers now, long ones held until the ball is out, "ball's out" first), 32-accessible-responsive-viewer.md (button semantics, live regions).

Build:
- pipeline/audiostands/answers.py: render answer fragments for the judge cut with the same voice and cache. That means 18 zone clips (2 teams × 3 sides × 3 thirds), 21 distance clips (0–100 m in 5 m steps), one score/clock clip per minute of the cut, "hold that thought" and "back to the action". Index them at web/public/replay/v1/judge/answers/index.json, and call this from build_bundle.
- web/src/ask/local-tools.ts: TypeScript versions of get_score_and_clock, get_ball_position (plus a spatial ball ping), get_last_events, what_did_i_miss and explain_moment (replays the cached cue audio), all clamped to the local playhead.
- web/src/ask/ask.ts:
  - One large native Ask button (a screen-reader double-tap is one activation; key A as a shortcut) that opens a short list of preset questions.
  - On a choice: the crowd ducks, the commentary queue pauses while the playhead keeps running, the answer plays, then "back to the action" plus a one-line catch-up of anything missed.
  - If a build line is due within 4 s, play "hold that thought" first. It says something is coming, never what.
- vitest:
  - for 200 random playheads, no answer uses an event with t > playhead (property test);
  - the catch-up covers exactly the events between the start and end of the Ask;
  - the button has an accessible name and works by keyboard.

Rebuild the bundle and redeploy with azd deploy.
Run it, verify it, commit and push.
```

**You do this manually:**
- [ ] **(20 min)** Try every preset at 3 different moments, including right before a goal. Does anything sound wrong, too long or spoiling?
- [ ] **(15 min)** Turn on Windows Narrator (Ctrl+Win+Enter) and operate Start, Ask and Settings with the keyboard only.

---

## Stage 7: Live spoken questions (Foundry Voice Live + Stats MCP server)

**Aim.** The fan presses Ask and speaks. Foundry Voice Live answers in the same voice as the commentary, calling our Stats tools, which are clamped to what the fan has already heard. The same tools are also served as an MCP server. **Time box: 7 h.** Presets stay as the fallback.

**Done when:**
- [ ] On the deployed URL, a spoken "Where's the ball?" mid-attack gets a zone answer in the commentator's voice with a ball ping, while the crowd is ducked.
- [ ] "Who scores next?" gets no spoiler.
- [ ] Stopping the relay (or `DEMO_MODE=off`) makes the presets take over within 8 s, and the fan is told so.
- [ ] `eval/report.md` has Q&A latency p50/p95 over at least 20 questions. There's no invented target; file 42 records a rival's 4.66 s median for comparison.
- [ ] Copilot Agent Mode can call our Stats MCP server from `.vscode/mcp.json`.

**Depends on:** Stage 6 (Ask UI), and the Stage 0 Foundry S0 resource. Voice Live needs no model deployment (file 44). **Time:** 7 h.

```text
Stage 7 of BUILD_PLAN.md: live spoken questions through Foundry Voice Live, with our Stats MCP server. Time box 7 h; the presets stay as the fallback.

Read first: CLAUDE.md; BUILD_PLAN.md Stage 7; in stoynev research/: 40-conversational-commentator.md (all of it: relay design, a) tools, b) relay, c) browser WebRTC, persona prompt, caps, the voice-name correction), 27-voice-speech-and-audio.md (Voice Live API, GA WebSocket api-version 2026-04-10), 43-audio-stands-architecture.md §1 (relay and MCP boxes), §3 (the 8 tool schemas), §7 (WebRTC is preview, 60-min session cap, fallback chain), 18-agentic-design-for-pipelines.md (MCP SDK v2: MCPServer, not FastMCP), 21-demo-uptime-cost-and-ops.md (per-IP limit, daily cap, DEMO_MODE kill switch), 30-infra-as-code-azd-bicep.md (Container Apps, user-assigned identity, role assignments, minReplicas override), 44-accounts-quotas-setup-checklist.md (Voice Live needs no deployment; S0 limits).

Build:
- relay/ (Python 3.12, FastAPI, one container):
  - tools.py: the 8 tools from file 43 over the judge-cut bundle, clamped to the listener's playhead. The browser posts {session_id, playhead_s}, and the relay injects session_id so the model never sets the clock.
  - mcp_server.py: the same tools as an MCP SDK v2 MCPServer over streamable HTTP at /mcp.
  - voicelive.py: a port of file 40's relay. It handles the SDP exchange for browser WebRTC and the server-side control WebSocket that answers function calls. Entra token from the managed identity (DefaultAzureCredential locally); model gpt-realtime-2.1-mini; voice = TTS_VOICE so answers sound like the commentary; persona prompt from file 40. If WebRTC fails, fall back to the GA WebSocket path.
  - Caps: per-IP limit, 30 questions per session, a global daily cap, a DEMO_MODE environment switch, close sessions after 90 s idle, reconnect before 55 min.
  - A Dockerfile.
- infra: a Container Apps environment and app (0.25 vCPU / 0.5 GiB, minReplicas 1, maxReplicas 2), a Basic ACR, and a user-assigned identity with Cognitive Services User on the Foundry resource; service "relay" in azure.yaml. No keys anywhere.
- web/src/ask/live-ask.ts: a "Talk live" mode on the same Ask button. The mic is open only between two presses; the crowd ducks to about 15% while listening; the answer audio goes through the same ducking bus. On any error, or no answer within 8 s, fall back to the preset menu and say so.
- .vscode/mcp.json: add our Stats MCP server next to Azure MCP, so Copilot Agent Mode can call it.
- eval/qa_latency.py: log end-of-speech → first answer audio for each question, and summarise p50/p95 into eval/report.md. Don't set a target; file 42's rival median of 4.66 s is for comparison only.
- pytest:
  - every tool clamps to the playhead (property test);
  - set_preferences never touches match state;
  - caps return a spoken refusal.

Deploy with azd up, then test from the deployed site.
Run it, verify it, commit and push.
```

**You do this manually:**
- [ ] **(5 min)** Approve the Container Apps deployment, and check the cost view the next morning. File 44 estimates the judging-period relay at about $2.92–9.72.
- [ ] **(30 min)** With headphones and a mic, ask 20 real questions at different moments, including off-topic and "who wins?". Note every bad answer.
- [ ] **(5 min)** Check Voice Live usage in the portal. File 43 estimates about $0.02 per question.
- [ ] **(15 min) Copilot and Azure MCP evidence (file 46).** In VS Code Agent Mode, ask Azure MCP "list Container Apps in rg-as-judge and their latest revision", and ask our Stats MCP "where is the ball at 3:10?". Take one screenshot of each for the README. Also do at least one small real task with Copilot Agent Mode, for example vitest cases for `haptics.ts`, and label that commit `ai:copilot`, so the hero-tech credit is honest.

---

## Stage 8: Polish for real listeners, accessibility CI and the listening test

**Aim.** Make it pleasant for a first-time blind listener and legible to a sighted judge:
- a "learn the sounds" intro;
- a visible sound radar for the muted video;
- Bluetooth calibration;
- axe-clean CI and an uptime check;
- a real eyes-closed listening test with at least 3 people.

**Done when:**
- [ ] CI passes, including Playwright + axe at 3 viewports with zero violations.
- [ ] The uptime workflow is green, and its badge is in the README.
- [ ] Narrator and TalkBack (or VoiceOver) walkthroughs are done with no blocker.
- [ ] `eval/listening_test.csv` has at least 3 participants, and `eval/report.md` shows the summary, whatever the result.
- [ ] Describer and Calm exist, **or** `docs/DECISIONS.md` says "Radio only".

**Depends on:** Stage 4. It uses Stages 5–7 if they're done. **Time:** 4 h, of which about 2 h is manual.

```text
Stage 8 of BUILD_PLAN.md: polish for real listeners. Learn-the-sounds, the visible sound radar, Bluetooth calibration, accessibility CI, uptime check and the listening-test kit; detail levels only if time remains.

Read first: CLAUDE.md; BUILD_PLAN.md Stage 8; in stoynev research/: 36-blind-fans-and-audio-description.md (Describer/Radio/Calm definitions, testing protocol, honest wording), 37-spatial-audio-in-the-browser.md (learn-the-sounds tutorial, Bluetooth latency), 32-accessible-responsive-viewer.md (Playwright + axe test, live regions, reduced motion), 42-audio-competitors-and-demo.md (sound radar and on-screen haptic pulse for a muted video, SDH captions), 41-haptics-match-tension.md (status via aria-live), 21-demo-uptime-cost-and-ops.md (GitHub Actions cron smoke test + badge).

Do these in order, and stop adding new items after 3 hours so there is time to deploy:
1. Sound radar: a visible pitch diagram with the ball dot, crowd level per end, a tension line, the haptic pulse and the current caption, for sighted friends and the video (aria-hidden, safe under reduced motion). Turn it on with ?radar=1 and from Settings.
2. "Learn the sounds": a skippable 2-minute guided intro to the ball rattle, the pass/shot/whistle icons, the crowd swell and the heartbeat, offered on the Start screen.
3. One-tap Bluetooth calibration: tap along to a beat, store the offset, apply it to haptics.
4. Playwright + @axe-core/playwright in CI at 3 viewports, with tags wcag2a, wcag2aa, wcag21a, wcag21aa and wcag22aa, plus reduced motion. Fix every violation.
5. .github/workflows/uptime.yml: a cron every 6 h that fetches the deployed URL and manifest.json; badge in README.
6. eval/listening_test.md: file 36's protocol (two 3-minute clips: commentary only vs full Audio Stands; comprehension probes "where was the ball / which side / was it dangerous / who scored"; RNIB's 15-point scale), eval/listening_test.csv to fill in, and eval/score_listening.py, which adds the summary to eval/report.md.
7. Only if time remains: Describer and Calm levels (planner variants, TTS and a detail-level setting). Otherwise ship Radio only and record that in docs/DECISIONS.md.

Rebuild and redeploy with azd deploy.
Run it, verify it, commit and push.
```

**You do this manually:**
- [ ] **(1 h 15 min)** Run the eyes-closed listening test with at least 3 people, about 20 min each, following `eval/listening_test.md`. Ask for consent before quoting anyone or filming a reaction for the video. Enter the results in the CSV.
- [ ] **(30 min)** Do a full walkthrough with Windows Narrator, then TalkBack on Android or VoiceOver on iPhone: Start, Ask, Settings, Next big moment.
- [ ] **(10 min)** Try the Bluetooth calibration with Bluetooth earbuds, if you have them.

---

## Stage 9: Video, write-up and submission (pinned: starts Mon 26, 13:00)

**Aim.** The video carries the score: the rules say judges need not watch past 2 minutes or test the project (file 12, brief). Make a video under 2:00 that works muted and on laptop speakers, a README mapped to the five criteria, and a pitch that names **only the Microsoft tech actually shipped**. Then submit early.

**Done when:**
- [ ] The video is 1:45–1:55 by `ffprobe`, Public on YouTube, not made for kids, with English SRT. It makes sense muted thanks to burned-in captions, including sounds like [crowd rises].
- [ ] The README has the judges' quick path, problem, five stages, architecture, agents and MCP, a results table from `eval/report.json`, the synthetic-data note, licences and an honest "How we built it".
- [ ] The repo is public; the demo URL works logged out in a private window and on a phone; the uptime badge is green.
- [ ] The form is submitted with the category **Best Use of Microsoft Foundry**, and you have a confirmation.

**Depends on:** Stage 4 at minimum; it uses whatever of Stages 5–8 exists. **Time:** 10 h (Mon 4 h + Tue 6 h), plus 2 h of buffer on Tue.

**Mon 26, 13:00, first prompt (scripts, captions, write-up):**

```text
Stage 9a of BUILD_PLAN.md: everything the video and the write-up need.

Read first: CLAUDE.md; BUILD_PLAN.md Stage 9 and "Not in this plan"; in stoynev research/: 14-demo-video-and-writeup.md (under 2:00, target 1:52, about 255 words of voiceover, beat structure, submission checklist, README skeleton), 42-audio-competitors-and-demo.md (muted-first video, radar, burned-in SDH captions, ffmpeg recipe, a real listener carries the story), 12-judging-criteria-and-rules.md (must-haves; no third-party trademarks or music), 46-copilot-github-azure-mcp-workflow.md ("How we built it", honest AI credit, AI-assist ledger), 36-blind-fans-and-audio-description.md (RNIB facts, honest testing wording), 43-audio-stands-architecture.md ("Pitch (3 sentences)"), 28-sponsor-goals-and-real-world-impact.md (impact framing). Use eval/report.json for every number; never put a number on screen that isn't in it or in a cited research file.

Create:
- video/script.md: a 1:52 script, about 255 words, as a table (time, on screen, voiceover, burned caption). Suggested beats:
  0:00–0:08 dark screen, crowd rises, "a seat in the stands for fans who can't see the pitch; synthetic match, real pipeline";
  0:08–0:20 problem (RNIB scored TV commentary 6.1/15; lag);
  0:20–0:45 hero moment on the radar: tension curve, the voice lifts about 4 s before the chance, crowd swell, heartbeat pulse, goal call, roar;
  0:45–1:05 Ask: "Where's the ball?" answered (live if Stage 7 shipped, otherwise preset, labelled as such);
  1:05–1:25 spoiler firewall: the Director sees the next 10 s and outputs only tension; eval numbers; trace screenshot;
  1:25–1:40 architecture with only the services we shipped, plus 5 s of Copilot Agent Mode + Azure MCP;
  1:40–1:52 a listener's reaction (with consent), "try it" URL, end card with the category and "AI voices · synthetic data".
- video/shotlist.md: exactly what to record, with URLs and flags (?radar=1, chapter keys, which question to ask), in order.
- video/voiceover.srt from the script, and video/captions_sdh.srt from the judge-cut cues for the match segment.
- video/narration.py: an optional Azure TTS narration of the script in a voice different from the commentator's, output to out/narration.mp3.
- video/assemble.sh: the file 42 ffmpeg recipe (burned captions, L/R level meter) as an optional finishing step; it must work with an LGPL ffmpeg build, so check each filter it uses.
- README.md, rewritten: demo link, video link placeholder and badges at the top; "Judges' quick path (60 s)"; problem; how it works (Ingest → Interpret → Explain → Render → Personalise); a Mermaid architecture diagram of what shipped; agents and MCP; results table from eval/report.json, with the realism report's red rows shown honestly; synthetic data note (generator, seed, judge cut); licences (assets/licences.json, dependency licences); "How we built it" (Claude Code for research and code, Copilot Agent Mode and Azure MCP where actually used, AI-assist ledger from git trailers); "What's next" (the "Not in this plan" list); team.
- SUBMISSION.md: title, tagline, an elevator pitch naming only the Microsoft tech we shipped (Foundry, Agent Framework, Voice Live, Azure Speech, Static Web Apps, Container Apps, Application Insights, Azure MCP, GitHub Copilot Agent Mode — keep only what is true), the category "Best Use of Microsoft Foundry" in the first line, links, and testing instructions for judges.
- Say "no public entry or product we found combines…", never "first" or "never done before" (brief).

Run it, verify it, commit and push.
```

**Tue 27, morning, second prompt (final checks before submitting):**

```text
Stage 9b of BUILD_PLAN.md: pre-submission checks.

Read first: CLAUDE.md; BUILD_PLAN.md Stage 9; stoynev research/12-judging-criteria-and-rules.md (submission must-haves) and 14-demo-video-and-writeup.md (submission checklist).

Do:
- Insert the YouTube URL I give you into README.md and SUBMISSION.md, and refresh every number from eval/report.json.
- Run the full CI locally (pytest, vitest, Playwright + axe) and the uptime check against the deployed URL; fix anything red.
- Scan the whole repo and git history for secrets (key-like strings, .env contents, connection strings) and for real club, player or commentator names; report anything found and remove it.
- Check that assets/licences.json covers every file in web/public/crowd/, and that no GPL dependency is in pipeline/, web/ or relay/ (list licences from the lockfiles).
- Check every link in README.md and SUBMISSION.md returns 200.
- Tag the commit v1.0-submission and write docs/FREEZE.md: from now on the judge environment only gets ops changes (the rules allow later edits only to remove infringing or PII material, file 12).

Run it, verify it, commit and push.
```

**You do this manually:**
- [ ] **(1 h 30 min, Mon)** Record the screen takes from `video/shotlist.md` with Clipchamp's screen recorder or the Windows Snipping Tool recorder, with system audio on. Record each beat 2–3 times.
- [ ] **(45 min, Mon)** Record the voiceover yourself with a decent mic, or run `video/narration.py` and approve it (15 min). Either way, label the AI voices on the end card.
- [ ] **(2 h, Tue)** Edit in Clipchamp to 1:45–1:55. Burn in captions, including the non-speech sounds; put the radar on screen during the match; keep all text readable on a phone at 720p. Use no music unless you made it yourself, and no logos.
- [ ] **(15 min)** Check the length with `ffprobe` (≤ 1:55). Watch once muted and once on laptop speakers.
- [ ] **(20 min)** Upload to YouTube as Public, "not made for kids", and upload the SRT. Give the URL to the 9b prompt.
- [ ] **(10 min)** Make sure the repo is public, or have its owner flip it. Open the repo and the demo URL logged out, in a private window.
- [ ] **(20 min)** Read the README and pitch aloud once, and cut anything you wouldn't say to a judge.
- [ ] **(30 min)** Submit on Innovation Studio: title, tagline, pitch, category, repo URL, video URL, demo URL and testing instructions. Screenshot the confirmation. **Target: 08:00 PT (15:00 London / 17:00 Sofia).**
- [ ] **(10 min)** After submitting, stop deploying feature changes to `judge`. Set calendar reminders for 31 Oct, 5 Nov and 10 Nov to open the demo, check the uptime badge and check the budget. Keep the demo up until at least 10 Nov 23:59 PT. Winners are announced by 20 Nov (file 12), so think about keeping it up until then; file 44 puts that at roughly $10–30 extra.

---

## Money and limits to keep in mind

These come from files 43 and 44 and were not recomputed for this smaller plan.

- **Total:** about $45–87 for the build week plus judging; plan for $100, with alerts at $50 and $100. This plan leaves out Event Hubs, Web PubSub and Cosmos DB, so expect less; that has not been recalculated.
- **TTS:** the F0 tier allows 20 transactions per 60 s and can't be raised; use the S0 Foundry resource. Whether HD voices work on F0 at all is (unverified).
- **Voice Live:** needs S0 (F0 is "Not applicable"); 100 new connections per minute, sessions of at most 60 min, 120,000 TPM. The quota form rejects Gmail and Hotmail addresses, so stay inside the defaults.
- **Foundry deployment:** capacity 10 = 10K TPM, which is also our abuse ceiling. A new subscription may start at 0 TPM (unverified, community report).
- **Static Web Apps Free:** 250 MB per app and 100 GB/month bandwidth (files 21, 43). The judge-cut bundle should be a few MB of audio.
- **Free credit:** it expires 30 days after sign-up. Upgrade to Pay-As-You-Go on day 0, or the account is disabled when the credit expires (file 44).
