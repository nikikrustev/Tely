# Decisions

_OWNER: A (potencialbg). Started 20 Oct 2026 in Stage 0. Newest decisions go at the bottom._

## D1. Scope: the one-person plan, split across two people (20 Oct 2026)

We build what `BUILD_PLAN.md` scopes for one person (Stages 0–9, 56 h), split between two people by
`TEAM_SPLIT.md`: A (potencialbg) owns everything Microsoft, B (Nikolay) has no Microsoft in his lane, and every
file has one owner. Each lane has about 25 h spare. We use it to bring the timeline forward and protect Stage 7,
not to add scope.

**Not in this plan.** These go under "What's next" in the README and stay out of the pitch:
- the live Event Hubs → Container Apps worker → Web PubSub path;
- Cosmos DB personalisation (settings stay in the browser);
- Bulgarian;
- game-controller rumble;
- "point your phone to listen" mode;
- native iPhone haptics (AHAP).

## D2. Region: Sweden Central (20 Oct 2026)

Sweden Central is the only European region with Voice Live realtime models, Global Standard `gpt-5.4-mini`, and
Speech HD voices (file 44). East US 2 is the fallback. West Europe has no Voice Live realtime models. Static Web Apps
go in `westeurope` (file 30; region list unverified).

## D3. Category: Best Use of Microsoft Foundry (20 Oct 2026)

From the brief and file 42, as `BUILD_PLAN.md` says. Our Foundry story: the Director agent on a Foundry model
(Stage 5), Azure Speech HD voices (Stage 3) and Voice Live questions (Stage 7).

## D4. Hard rules (from CLAUDE.md)

- Synthetic data only. No StatsBomb open data, and no xT or EPV grids derived from real matches.
- No Ultralytics and no GPL code, dependencies or build tools.
- Fictional clubs and players, CC0 crowd clips only, and every AI voice labelled as AI.
- Keys: keyless auth (`az login` / managed identity) first; keys only from a git-ignored `.env`. Nothing prints,
  logs or commits a key. CI never needs Azure credentials.

## D5. Repo seams (20 Oct 2026)

- Azure Python SDKs live in `pipeline/requirements-azure.txt`, not `pipeline/pyproject.toml`. CI installs only
  `pyproject.toml` and fails if a Microsoft package appears there or in `web/package.json`.
- Tests are split by folder (`pipeline/tests/{a,b}`, `web/tests/{a,b}`). pytest uses `--import-mode=importlib`,
  so both folders can hold files with the same name.
- The model deployment is pinned with `versionUpgradeOption: NoAutoUpgrade` through an ARM PUT, because
  `az cognitiveservices account deployment create` has no flag for it.

## D6. No money: stay on the Azure free account, never upgrade (20 Oct 2026)

The team spends no money while building. That overrides file 44 and BUILD_PLAN's "upgrade to Pay-As-You-Go straight away".
- **Why it works:** a free account has a spending limit equal to its $200 credit. "When your usage results in charges
  that exhaust your spending limit, the services that you deployed are disabled". Nothing is charged to the card
  (Learn, "Azure spending limit", accessed 20 Oct 2026). Upgrading removes the limit, so we don't upgrade.
- **Still charged even with the limit:** Marketplace and third-party services, support plans and Entra ID P1/P2. We use none of them.
- **Time:** the credit lasts 30 days from sign-up (about 20 Nov if we sign up on 20 Oct), which covers judging to 10 Nov.
- **Risk 1: model quota.** Free trials can get 0 TPM on some models (file 44). If `gpt-5.4-mini` has none, the Director
  uses rules (drop-list item 5), which costs $0.
- **Risk 2: running out of credit takes the demo down.** File 44 estimates $45–87 in total, well under $200. Keep the $100
  budget alert at 50% and 100%, and never use `minReplicas` > 0 or a paid SKU we don't need.
- The card still gets a $1 temporary hold at sign-up (file 44).

## D7. Director model: gpt-5-mini, because gpt-5.4-mini has no Free Tier quota (21 Oct 2026)

The bootstrap on our free account reported quota tier **"Free Tier"**, and deploying `gpt-5.4-mini` GlobalStandard
failed with `InsufficientQuota` (limit 0). `az cognitiveservices usage list -l swedencentral` shows non-zero limits for
`gpt-5-mini` GlobalStandard (500, in thousands of TPM), `gpt4.1-mini` GlobalStandard (200), `o4-mini` (100) and
`gpt-realtime-mini` (40). We deploy **`gpt-5-mini`** for the Director instead of filing the quota form, which may not
apply to a free account. `.env` uses `FOUNDRY_MODEL=gpt-5-mini`. If the Free Tier later moves up, we can switch back.

## D8. Voice Live works on the Free Tier: GPT Realtime Mini, Standard tier (21 Oct 2026)

potencialbg tested the Voice Live playground in project `tely` (resource `as-foundry-stoynev`, Sweden Central) on our
free account: it heard the question and answered by voice. The playground lists models by price tier (Pro / Standard / Lite)
without version numbers. We use **GPT Realtime Mini (Standard)**, which matches `gpt-realtime-mini` in our quota list (40)
and the plan's `gpt-realtime-2.1-mini`. The exact version behind the name is (unverified). Avoid the Pro models, which cost more.

## D9. Stage 3 commentary: what we verified and what we chose (21 Oct 2026)

Built against B's hand-written 90 s sample (`contracts/b/sample/`), because Stage 1 has not merged. Every Stage 3 reader
goes through `tely.commentary.source.load_match()`. Switching to the real cut is one line in `MATCH_DIRS`.

**Verified on our resource (`as-foundry-stoynev`, keyless):**
- `get_voices_async("en-US")` lists 30+ `en-US-*:DragonHDLatestNeural` voices, incl. Andrew, Brian, Ava, Davis, Emma, Steffan.
- All five style tags we use (`calm`, `curious`, `urgent`, `excited`, `shouting`) are silent: we rendered each with Andrew HD
  and transcribed the audio with Speech-to-text; no tag word was spoken. Andrew HD measured about 2.6 words/s, as file 39 assumed.
- HD output differs slightly on every render (file 43 §7), so we never re-render a cached SSML hash.

**Choices (ours):**
- B's `reveal_t` comes 0.4–0.7 s after the shot. A "shoots!" call at shot + 0.2 s rarely fits before the outcome, so the
  outcome line ("Saved!", "Goal!") is placed first, at `reveal_t`, and the call appears only when the ball travels long enough.
- Hush: no describe or fill line may start between a build-up and its reveal.
- Build-ups carry shorter fallback texts and are never dropped for length (BUILD_PLAN: never cut the build-up).
- The spoiler-leak eval is stricter than file 43: an outcome word is a leak from D before the shot **until its `reveal_t`**.
- DragonHD `temperature=0.4` (BUILD_PLAN: "low"). The style tag is repeated per sentence, since a tag ends at a sentence boundary.
- Rendered-but-rejected fallback MP3s stay in the cache: they are what lets a rebuild make 0 TTS calls.

## D10. Stage 3 on B's real judge cut (21 Oct 2026)

`MATCH_DIRS["judge"]` now points at B's Stage 1 bundle. The tests build both the sample and the judge cut.
- **VAR (contract 0.2.0):** `reveal_t` is the decision, about 22 s after the ball goes in. During the wait we say that a check
  is happening ("It's in the net... but hold on, VAR is checking it", then "Still checking..."), never the verdict. "Net" is
  not an outcome word: the ball going in is a fact at that moment, and whether the goal stands is not.
- **Opener and kits are split:** the cut opens 5.4 s before the first build-up, so the AI label goes first, and the kits and
  direction line takes the first quiet slot (716 s in this cut).
- New lines: yellow card, free kick, goal kick (never the word "goal"), block with the blocker's name, wide, offside.
- Judge cut, Andrew HD: 45 lines, truth_check 45/45, 0 spoiler leaks, longest gap between line starts 19.1 s, rebuild 0 TTS calls.

## D11. Replay bundle and hosting (A3, 21 Oct 2026)

- **`build_bundle`** runs B's `build_match`, then `build_commentary`, then B's `build_segments` (skipped until B's Stage 2 exists),
  then writes `manifest.json` (file 43 §6 shape, sha256 of every file). Cues stay out of `segments.json` (TEAM_SPLIT.md).
- **gzip across machines:** B's `ticks.json.gz` re-compresses to different bytes on our Python 3.12 / zlib 1.3.1 than on B's
  machine. The unzipped data is identical. `build_bundle` writes B's original bytes back in that case, so git stays clean; any
  real content change stops the build (exit 2) as a determinism bug for B.
- **Chapters are spoiler-safe:** one "Big moment N" stop 6 s before every build-up and card, the same for a goal or a miss.
- **Hosting:** Static Web Apps **Free only** (D6), in West Europe (superseded by D12: East US 2). Verified 21 Oct with `az provider show`: SWA regions are
  Central US, East US 2, West US 2, West Europe, East Asia (no Sweden Central). The resource group stays rg-as-judge in Sweden
  Central, where the bootstrap created it.
- **Caching:** only the hash-named MP3s and Vite's `/assets/*` are `immutable`; the rest of `/replay/*` revalidates after
  5 minutes, because `cues.en.radio.jsonl` keeps its name when rebuilt. `.gz` is served as `application/gzip`, so the
  browser gets raw bytes and decompresses them itself.

## D12. Stage 4 deploy and the browser commentary track (22 Oct 2026)

- **Static Web Apps moved to East US 2.** The first `azd up` failed validation in West Europe with `RequestDisallowedByAzure`
  ("The selected region is currently not accepting new customers"). Nothing was created. East US 2 deployed first time.
  On Free, the region only hosts the app's metadata; the static files are served from the global edge (file 21).
  The resource group stays in Sweden Central.
- **MVP live:** https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/ (env `judge`, rg-as-judge). Checked in Chrome: 70 requests,
  all `GET 200` to that one host (HTML, JS, JSON/JSONL, MP3); no API, no third party.
- **azd uses the az CLI login** (`azd config set auth.useAzCliAuth true`, user-level azd config, chosen by potencialbg).
- **Two audio clocks.** `LaneBContext` gives lane A no AudioContext, and B's context only exists after Start's awaits, so the
  voice has its own context, unlocked in the same tap, and maps match time from `ReplayClock.now()` (median of 15 samples,
  re-measured on every play/pause/seek). Measured: lines land within 5 ms of `t_in` in simulation and 0-3 ms in Chrome.
  If B appends the context to `LaneBContext`, we can drop the second clock.
- **Late lines skip their own leading silence.** The playhead holds at t0 during `ReplaySource.play()`'s 0.3 s head start, so
  the first line is found a few ms late. All 45 Andrew HD MP3s open with 46-72 ms of silence (measured by decoding in Chrome),
  so skipping up to that much keeps speech on `t_in` without cutting a syllable.
- **Duck:** -12 dB (file 38's +12 dB speech rule; B adds a -6 dB 2 kHz dip), 150 ms attack starting 0.25 s before each
  line, 600 ms release 0.35 s after it. Holds are counted, so lines closer than that share one duck.

## D13. Commentary voice: Brian HD, picked by ear (22 Oct 2026)

- **potencialbg picked `en-US-Brian:DragonHDLatestNeural`** from the `out/voices/` samples (Andrew, Brian, Ava), closing the
  Stage 3 "pick a voice by ear" item. `.env.example` now defaults to Brian; `ssml.py`'s `DEFAULT_VOICE` stays Andrew so the
  mocked test hashes don't change, and real builds read `TTS_VOICE` from `.env`.
- **Re-render:** the old Andrew MP3s were deleted first, because the SSML-hash cache never prunes files, so they would
  otherwise ship and be listed in the manifest. Result: 58 TTS calls, **48 lines** (was 45), truth_check 48/48, 0 spoiler
  leaks, both build-ups exactly 4.0 s before their shots, longest gap between line starts 18.2 s; 2.3 MB bundle.
- **Why 48 lines:** the planner uses the real MP3 durations, and Brian is a little faster (204 s of speech against Andrew's
  215 s), so three short describe/call lines now fit. One build-up switched to its shorter fallback ("Navy coming...").
- **Leading silence:** Brian's 45 MP3s open with 67-88 ms of silence (decoded in Chrome); the late-line skip measures each
  buffer, so nothing in the code changed.
- **Deployed** with `azd deploy`; the live manifest lists Brian, and in Chrome the first lines started on their `t_in` spacing
  with only same-origin requests.

## D14. Copilot Agent Mode + Azure MCP verified (22 Oct 2026)

- **Set-up:** VS Code 1.143.0, GitHub Copilot (Free) in Agent Mode, and the Azure MCP Server from `.vscode/mcp.json`
  (`@azure/mcp@3.0.0`, `--read-only`), started from its Start link with our subscription ID entered at the prompt.
- **Test (potencialbg):** Agent Mode was asked to list the resources in `rg-as-judge` through Azure MCP. Its answer:
  one resource, `swa-as-judge-calef3`, a Static Web App (`Microsoft.Web/staticSites`) in `eastus2`. That matches D12.
- **What it hit:** the first request failed with a tenant mismatch. Giving the subscription's tenant fixed it.
- **Evidence:** potencialbg kept a screenshot of the answer for the README and the "How we built it" section. This is
  the BUILD_PLAN Stage 0 Copilot item; A7 still needs the Container Apps question and one real `ai:copilot` commit.

## D15. Commentary density: a ball line at least every ~9 s in play (23 Oct 2026)

- **Why:** Nikolay's listening note on PR #11 said the commentator went quiet for too long. D13's judge cut had 18.2 s
  between line starts with the ball in play (894.68 → 912.88). A blind listener needs to hear where the ball is
  often (file 36 rule 1, ball-first grammar, Radio level).
- **Planner (`planner.py`):** a new ball-fill pass runs after the event lines are placed and before the old state fill.
  `in_play()` reads the stretches where the ball is alive from B's 25 Hz ticks, and `quiet_in_play()` finds every
  stretch with the ball in play and no line starting. Any stretch longer than `BALL_EVERY_S` = 9 s is cut into equal
  parts with ball lines. Each ball line needs 1.5 s of silence on both sides, or at least the 0.6 s the crowd duck
  needs (0.25 s before a line plus 0.35 s after it, D12). Ball lines are in `HUSHED`, so the gap between a build-up and
  its reveal stays clear, and they are spoken only while the ball stays alive for the whole line. Dead-ball
  stoppages (VAR, celebrations, the yellow card) are still covered only by the old 20 s state rule.
- **Wording (`templates.ball`):** location, team, then name ("Midfield, far side, Navy keeping it."), with phrasings
  picked by a seeded RNG. A player is named only once the ball has reached them (a completed pass's receiver or an
  interceptor), never while the pass is in the air, and not after a block or a save. If the line before or after
  already names that player, the ball line leaves the name out, and gives the score instead when nobody has said it
  in the last 60 s. The shortest fallback is "Attacking third, Reds.": real Brian durations run longer than the
  estimate ("Midfield, far side, Reds." takes 3.0 s), and without it one stretch stayed at 10.6 s.
- **Result (judge cut, real Brian HD durations):** **70 lines (was 48)**: 22 of them are ball lines, and the other 48
  are unchanged. The longest stretch with the ball in play and no line starting is **9.0 s (was 18.2 s)**. The longest
  gap between line starts is now 17.0 s (950.25 → 967.28), during the dead-ball yellow-card stoppage, as intended.
  Speech: 279 s of the 480 s window (was 204 s). Both build-ups are still exactly 4.0 s before their shots.
  truth_check 70/70, 0 spoiler leaks, and no overlaps; the narrowest silence beside a ball line is 0.60 s.
- **TTS:** **36 calls** in all (31, then 5 more for the short fallbacks). A rebuild makes 0 calls, and
  `test_second_build_makes_zero_tts_calls` checks that the cue file comes out byte-identical. B's files came out unchanged. 94 MP3s (3.4 MB bundle): 64 are used by cues. The other 30 are fallback texts whose
  real durations the final plan reads, so they stay: deleting them would change the next plan and cost new TTS calls.
- **Tests:** `test_ball_in_play_is_never_quiet_for_more_than_10_s` holds the judge cut to 10 s, both as built with
  mocked durations and as committed with real ones. The sample cut is exempt: its 11.5 s stretch is its 9.3 s kits
  line. Other new tests check that ball lines are ball-first, contain no outcome words, leave room for the duck, vary
  their wording, and never name a receiver while the pass is still in the air.
- **Deployed** with `azd deploy -e judge` from this branch, which already contains B4 (#12). Checked in Chrome: the
  site plays with the B4 UI. All 98 requests went to the one host and returned 200. The live manifest lists 104 files
  and Brian, the 70 cues include 22 ball lines, exactly the 64 cue MP3s were fetched, and the console showed no
  errors.

## D16. Stage 5: the Director on Foundry, its firewall, tracing and the eval (23 Oct 2026)

- **Quota is there, so `DIRECTOR=foundry`.** `scripts/smoke_azure.py` passed for `gpt-5-mini` (D7) on 23 Oct, so the rules-only
  fallback (BUILD_PLAN drop-list item 5) was not needed. The Director is an Agent Framework `Agent` on `FoundryChatClient`
  (`agent-framework-core` 1.23, `agent-framework-foundry` 1.15; keyless), with strict JSON-schema output and
  `reasoning.effort = minimal`.
- **One window per shot, not per 10 s tick.** The Director first learns of a shot when truth time reaches it (file 43 §2), so
  each shot is one window [shot − D, shot] and one call. A shot less than 10 s after the last call is planned by rules and logged
  as `budget` (file 43 §4: at most one call per 10 s). The judge cut has 4 shots, so **4 calls, about 490 tokens each**.
- **The firewall is an allow-list.** `features()` copies event types, sub-types, attacking/defending, zones, xG, body part,
  seconds to the shot, minute, score and tension at P and 4 s before the shot. It never copies `outcome_type`, the shot's end point, VAR,
  related saves/blocks, or B's `spoken`/`spoken_past` text. A test rewrites each shot's ending and checks the features are
  byte-identical.
- **The Verifier is code.** It checks the schema by hand (types, ranges, enum, no extra fields), plus two facts: `counter` needs a
  regain by the attacking team in the window, and `set_piece` needs a set piece. The very first live reply (`build_up_level 2,
  lead_s 1, hold_ms 1200`, before the prompt gave ranges) is now a test case it must reject. `lead_s` is held to 3.5–4.5 s (Stage 3:
  LEAD_S ± 0.5), which keeps at least 5.5 s of the 6 s wall budget. Then truth_check + spoiler_check run on every text the build-up
  may speak. Any failure (429, timeout, quota, bad JSON, schema, a failed check) sends that window to the rules Director, and the
  reason is logged.
- **The rules Director is Stage 3, byte for byte.** `DIRECTOR=rules` rebuilds the judge cut with 0 TTS calls and only the new
  `source.director` field changed. So falling back can never make the show worse than the MVP.
- **What the plan changes.** `build_up_level` (below 0.3: no build-up; else the voice intensity and style band), `lead_s`, `hold_ms`
  (an SSML break after the line) and `hint_type`, which picks the tail ("on the break!", "from the set piece!", "real danger here!").
  A hold is dropped before any words are: the planner tries each text with the hold, then without, then the next shorter text.
  A new short tail ("Reds... Orlani... danger!") keeps the hint when only 3.8 s are free before the reveal.
  A build-up must now also **end by its shot** (planner, strict pass first; it runs on only if no text fits): a shorter
  Director tail once let "Attacking third, Navy... Olvholm... here's a chance!" run 1.5 s past the header and push out the call
  "Fenford, the header!". Every Stage 3 build-up already ended by its shot, so the rules output is unchanged (checked).
- **Result on the judge cut (Brian HD):** the Director built up for the same two chances as the rules (xG 0.217 and 0.083) and
  skipped the two hopeful shots (0.014, 0.011). It chose "danger" for both and a 300–350 ms hold. 70 lines (same as Stage 3),
  truth_check 70/70, **0 spoiler leaks**, 10/10 spoken numbers verified, 0 fallbacks. Build-ups: "Navy coming... Olvholm...
  here's a chance!" and "Reds... Orlani... danger!". 13 new MP3s (117 files, 3.8 MB). One orphan MP3 from a discarded hold
  variant was deleted, and every cached MP3 is read by the replay plan or the rules plan (0 orphans).
- **Replay keeps the bundle deterministic.** `DIRECTOR=foundry` records every reply to `pipeline/tely/agents/recorded/judge.json`
  (features, raw reply, latency, tokens; no keys or audio). Without `DIRECTOR` set, `build_bundle` replays that file, so a rebuild,
  CI, or Nikolay gets the same plans with no Azure. If B's match changes, the replay no longer matches, those windows fall back to
  rules, and a test fails, asking for a re-record.
- **Tracing:** a workspace-based Application Insights `appi-as-judge` + Log Analytics `log-as-judge` (1 GB/day cap) were added to
  `infra/` and provisioned with `azd provision`. The connection string lives only in the git-ignored azd env.
  `configure_azure_monitor()` + `enable_instrumentation()` (file 18 §5); prompt text isn't captured. Verified with a Log
  Analytics query: `workflow.run`, `executor.process director|commentator|verifier|tts`, `invoke_agent Director`, `chat gpt-5-mini`
  under service `tely-director`. The App Insights resource is not linked to the Foundry project, so the Foundry "Traces"
  tab stays empty (manual step if we want it there).
- **Seen in the traces:** each new `DefaultAzureCredential` first probes the managed-identity endpoint on a laptop (~1 s per
  token fetch) before it uses the az login. The token is then cached, and the real-time harness opens connections with one
  untimed warm-up call.
- **Numeric truth on Foundry:** the same `grade()` from file 18 ran as a code-based custom evaluator (preview,
  `beta.evaluators.create_version` + an OpenAI-style eval run): `tely-numeric-truth`, 4/4 items passed, matching the local grader.
- **Real-time latency (`python -m tely.eval --realtime`):** plan → verify → TTS per build-up, from the moment the shot
  enters the look-ahead to the moment its MP3 exists, against D − lead_s. Wall clock, 1 run: 2/2 within budget, 3.75 s each.
  Waits ÷10, 5 runs: 10/10 within budget (5.8–6.0 s), p50 2.98 s, p95 3.56 s (plan p95 2.41 s, TTS p95 1.64 s). Each run opens
  its connections with one untimed warm-up call. The cold first call on 23 Oct took 6.2 s, which alone would miss the budget,
  so a live service must warm up before kick-off.
- **Skipped (BUILD_PLAN "optional, only if < 3 h used"):** LLM colour lines. The stage took longer than 3 h, so every spoken line
  stays a template, and the report says "LLM lines: 0".
- **A/B listen still to do (potencialbg):** rules vs Director differ only in the two build-ups' wording ("this could open up!" →
  "here's a chance!"; "Reds coming... Orlani... space opening up!" → "Reds... Orlani... danger!") and the hold. Record the pick here.

## D17. Stage 7: live spoken questions through Voice Live, the relay and its numbers (23 Oct 2026)

- **WebSocket through the relay, not browser WebRTC.** BUILD_PLAN made WebRTC primary and the GA WebSocket the fallback.
  We built only the WebSocket path. WebRTC is preview (`2026-01-01-preview`), and file 40 §2 found its event routing
  ambiguous. Through the relay, every event (VAD, both transcripts, tool calls, audio) passes one place, so tool calls,
  golden turns and latency are complete. The cost is one extra hop for the audio (PCM16 24 kHz, ~48 kB/s, only while
  asking or answering).
- **What runs:** Voice Live API `2026-04-10` (GA) and `gpt-realtime-2.1-mini` (Standard, D8), answering in the commentary
  voice `en-US-Brian:DragonHDLatestNeural` (D13), with `azure_semantic_vad` (500 ms) and `gpt-4o-mini-transcribe` for
  the question text. Auth is keyless: the user-assigned identity holds Cognitive Services User + Foundry User on
  `as-foundry-stoynev`, and locally it is `az login`.
- **B's brain is imported, not copied.** `TOOL_SCHEMAS`, `PERSONA` and `call_tool` come from `tely.qa`. The
  playhead is the one in the browser's `ask` message (the moment the fan pressed), clamped to the cut. It is never
  extrapolated, so it can't run ahead of what the fan heard. Tool outputs go back only after the `response.done` of the
  response that called them. Sending them earlier raced the model's own preamble response (smoke test, 23 Oct).
- **B's MCP server is mounted at `/mcp`** in the same app. Its session manager runs in the relay's lifespan (a mounted
  Starlette app's lifespan doesn't). DNS-rebinding protection stays on, with our host name in `MCP_ALLOWED_HOSTS`.
  `.vscode/mcp.json` lists it next to Azure MCP, with the playhead as an input (default 860 = 59:20).
- **Caps (ours):**
  - 30 questions per session, 4 tool calls per answer, 300 output tokens;
  - close after 90 s idle, a fresh Voice Live connection after 55 min;
  - 200 questions a day;
  - per IP: 6 sessions per 10 min and 2 open at once; 60 MCP calls per minute;
  - `DEMO_MODE` live/off.

  Every refusal is spoken, from 5 clips rendered in the commentary voice (`relay/clips.py` → `web/public/replay/v1/judge/live/`).
  The per-IP cap fired during our own testing: 4 headless sessions plus browser runs from one machine.
- **Scale to zero, not `minReplicas 1`** (D6 overrides BUILD_PLAN). The page calls `/health` on load to wake the relay.
  The first request after idle took over 30 s, so a fan who presses Ask before the relay is awake hears "Live questions
  aren't available right now" and gets the presets.
- **The live Ask has its own AudioContext.** `CommentaryTrack.pause()` suspends the commentary's context, and B pauses the
  commentary before every answer, so the mic worklet and the answer audio would never run on it. Found with Chromium's
  fake mic. The clip and playback waits now also time out, so a suspended context can't hang the Ask.
- **Latency is measured in the relay.** The VAD's `audio_end_ms` counts from the last `input_audio_buffer.clear`, not
  from session start (measured: the second question of a session read 7.2 s until the relay reset its audio clock per
  question). `facts_latency_ms` runs to the first audio after the tool results went back, so a "Let me check" preamble
  doesn't flatter it.
- **Persona fixes on our side.** The first 31-question run said "I'm an AI voice" 26 times, often twice per answer: the
  pre-tool and post-tool responses each took themselves for B's "first answer". The relay now adds one system note after
  the disclosure, and a hosting note that the tools are instant. Second run: 5 mentions (about one per session), median
  answer 39 words (was 44). The "Let me check" preamble mostly stayed. The model now says "Ball first:" out loud; that
  wording is B's (HANDOFF).
- **Image build without Docker or ACR Tasks.** The free subscription refuses ACR Tasks (`TasksOperationsNotAllowed`), and
  A's machine has no Docker, so azd can't build the relay. `relay/push_image.py` takes `python:3.12-slim`, adds one layer
  (the same files as `relay/Dockerfile`, plus Linux wheels resolved by `uv`), and pushes it with the user's own
  `az acr login --expose-token`. The azd `predeploy` hook (`relay/deploy.py`) points the app at it and saves
  `RELAY_IMAGE`, so `azd up` still deploys everything. `relay/Dockerfile` stays the reference build.
- **Results (deployed, 23 Oct):** B's 31 eval questions, spoken by a TTS "fan" voice and streamed in real time by
  `eval/qa_latency.py run`: **31/31 answered, 0 spoiler hits** on B's spoiler words. "Who scores next?", "Who wins?" and
  "What's the final score going to be?" all got "that's for the match to decide"; odds and betting got the redirect.
  Latency: first audio **p50 1.14 s, p95 1.82 s**; to the facts p50 2.66 s, p95 3.35 s. A rival's median is 4.66 s
  (file 42), for comparison only. From the deployed page (Chromium with the question as its fake mic): 5 answered.
  With `DEMO_MODE=off` and with an unreachable relay, the refusal came within 0.2 s of `live.ask()`, and the presets
  opened 4.8 s later, after the spoken reason.

## D18. Radio only: the Describer and Calm detail levels are dropped (24 Oct 2026; superseded by D30: two levels)

- **What ships:** one detail level, **Radio** (file 36 rule 3: the ball and key moments, with short pauses). The bundle
  has one cue track (`manifest.json` `tracks.en.radio`), and the page has no detail-level setting.
  **Describer** (continuous, with off-ball shape) and **Calm** (goals, chances, cards and the score every 5 min, with
  vibration carrying the rest) are not built.
- **Why:**
  - BUILD_PLAN puts this first on the cut line ("Describer and Calm detail levels: ship Radio only"), and Stage 8
    item 7 says to build them only if time remains. It doesn't: the listening test runs on the morning of Mon 26 and
    Stage 9 (video and submission) is pinned to 13:00 that day.
  - Each level is a whole new commentary track, not a switch. It needs a planner variant, new templates, TTS for
    every new line, and the truth check, spoiler firewall and eval run again on it. Shipping that untested two days
    before the deadline would risk the one track that is already verified (D16: 0 spoiler leaks, 70/70 truth check).
  - The listening test (`eval/listening_test.md`) compares commentary alone against full Tely. Adding a
    detail-level comparison would split 3 participants across too many conditions to say anything.
- **What covers part of the need today:** asking "where is the ball?" at any moment (offline presets and live
  questions), the crowd slider, and vibration set to key moments only. None of these is a detail level, and the
  write-up must not claim one.
- **Known loose end:** the Q&A tool `set_preferences` (`pipeline/tely/qa/__init__.py`, `tools.py`, and the MCP
  server) still offers `verbosity: describer | radio | calm`. The page drops it (`web/src/settings.ts` `prefsPatch`),
  so a fan who asks for less talk can hear "done" when nothing changed. Follow-up: take `verbosity` out of the tool
  so the commentator says it can't do that yet. The relay has to be redeployed after that change.
  **Fixed the same day (`a/no-verbosity`):** the schema and the MCP tool take only `crowd_mix` and `haptics`; a
  `verbosity` the model sends anyway gets "I can't change how much I say yet…" instead of "Done."; the persona tells
  the commentator the same. Live only after the relay is redeployed.
- **If time does turn up before the deadline,** TEAM_SPLIT.md's stretch order still applies: LLM colour, then the
  Foundry cloud evaluator, then Describer/Calm audio.

## D19. Tester mode (`?test=1`) and its feedback in Application Insights (24 Oct 2026)

- **What:** a guided test for friends who don't know the project, only at `/?test=1` (`web/src/tester/`). A plain
  welcome with the two consent questions from `eval/listening_test.md` section 3 (take part; anonymous quotes), eight
  tasks (sound tour, two eyes-closed clips with the section 5 probes as multiple choice and the section 6 scale,
  Ask, Settings, overall feedback), "Report a problem" (button and F), and a thank-you screen with "Copy my
  answers". No name, email or age is ever asked for. The mailto fallback is off until we pick an address
  (`FEEDBACK_EMAIL` in `web/src/tester/index.ts`).
- **The judges' path doesn't change.** `main.ts` imports the tester module only with `?test=1`. The markup is a
  `<template>`, which is inert, so without the flag none of it is in the DOM, the accessibility tree or the tab order.
  `web/tests/a/tester.spec.ts` checks that: no `t-*` element, no tester request, Start focused, and F does nothing.
- **Listening test, self-run group.** The tester ID is `t-` plus 8 random hex digits, made on the first visit. Its last
  digit picks the section 1 group (even A, odd B). Each clip task sets from/to/sound inside the page, never in the
  URL or on screen. The probes are scored in the browser against section 5's key, and the score is sent but never
  shown. `eval/pull_feedback.py` appends testers who answered both clips to `eval/listening_test.csv` with
  `mode=self` and sight "sighted, eyes closed" unless they told us otherwise. `score_listening.py` and
  `build_report.py` report them apart from the moderated sessions and say they are not blind fans (file 36). The
  task order is fixed (the tour is always first), unlike the moderated protocol, which plays the tour before the
  full-sound clip only.
- **Why Application Insights:** it's already provisioned (D16, `appi-as-judge`, 1 GB/day workspace cap), it's free
  at this volume (about 15 events per tester, each under 4 KB), and it's on the Microsoft stack we name in the pitch.
  We need no new database, storage account or third-party form, and nothing to pay (D6). The relay's
  `POST /feedback` checks a flat schema (no free-form keys, 4 KB body, text trimmed and capped at 500 characters),
  then logs one custom event, `tester_feedback`, through the Azure Monitor OpenTelemetry distro (`relay/telemetry.py`).
  Only that one logger is exported. Tracing, metrics, live metrics and auto-instrumentation are off, so the relay
  sends nothing else.
- **Privacy:** the client IP is used only for the in-memory rate limit and is never put in the event. The browser
  sends the user-agent family (for example "chrome", "android"), never the string. Free text can hold personal
  details, so `pull_feedback.py` writes it only to git-ignored `out/feedback/feedback.csv`, and the public listening
  CSV gets no free text at all. App Insights keeps it for the workspace's 30 days. One exception the tester is told
  about: a question asked out loud goes to Voice Live, and its transcript is in the relay's console log (D17's golden
  turns).
- **Caps (ours, D17 style):** per IP 60 events per 10 minutes, and 3000 a day (`DAILY_FEEDBACK_CAP`). Only the Static
  Web App origin may post (`FEEDBACK_ORIGINS`, set by `infra/relay.bicep`). Other routes still allow only GET in CORS.
- **Never lose an answer:** each event is saved in localStorage first (wrapped in try/catch: blocked storage keeps it in
  memory), then sent with `fetch` + `keepalive` as `text/plain`, a CORS simple request, so there's no preflight. It's
  retried once after 30 s, because a cold relay takes over 30 s (D17). Events still unsent are retried on the next
  visit and are in "Copy my answers" (an `AS1.` code line that `pull_feedback.py --paste` reads). Each event has an
  ID, so a retried event counts once.
- **Infra:** the App Insights connection string reaches the relay as a Container Apps secret (`@secure()` param),
  never a plain env value or a file. `relay/requirements.txt` adds `azure-monitor-opentelemetry`. CI still installs
  only `requirements-test.txt`, and the tests mock telemetry.
- **Deployed and checked (24 Oct):** `azd provision` (the secret and `FEEDBACK_ORIGINS`) then `azd deploy` (relay
  revision 9, web). A full run in the built-in browser on the live `?test=1` (tour, both clips to their automatic
  end, both question sets, Ask with 2 presets, Settings, overall feedback in Bulgarian, one problem report, thank-you
  screen) sent 15/15 events. All 15 arrived in `customEvents` as `tester_feedback` from `tely-relay`, with
  `client_IP` 0.0.0.0, and `pull_feedback.py --dry-run` read them back (Cyrillic intact). Two fixes came out of the
  run: azure-core's HTTP logging flooded the console (now WARNING), and `az` on Windows dropped Cyrillic from piped
  output (KQL now returns the dimensions base64-encoded). The tester and a11y specs passed against the live site,
  apart from the two checks that assume no relay (now switched by `A11Y_BASE_URL`). Those runs, and Claude's, are
  skipped by `pull_feedback.py` (`TEAM_TESTS_BEFORE`).

## D20. The match mix: no ball sound, crowd follows the ball, press-box commentator, `?mix=1` mixer (24 Oct 2026)

- **Why:** from a seat on the halfway line nobody hears a ball on grass. The looped band-passed noise (the "ball") was
  a constant hiss, passes and shots popped out of the crowd, and the commentator sounded as if he were on the pitch.
- **No ball sound:** `SoundStage` no longer has the noise loop, rattle, ball panner or ball send. `ballAt()` only
  records where the ball is (by audio time, so "Where is the ball?" pings where it is now, not where it is queued).
- **Left/right without it (three cues):** (1) passes, shots, tackles and saves stay panned by ball x (HRTF + stereo);
  (2) `CrowdEngine.followBall()`: the crowd end nearest the ball lifts and the far end drops (±3.5 dB at `nearEnd` 0.5,
  up to ±7 dB), for the end beds, chants and crowd reactions; (3) the anticipation layers (swell, tense) pan toward
  the ball (0.7 × side), like the part of the stand nearest the action. The home end stays left (`homePan` -0.5).
- **Kicks under the crowd:** pass -14 dB, shot -9, tackle -12, save -10 against the old levels, through a 2.4 kHz
  low-pass and twice the whistle's reverb send. The whistle (-2 dB) and the ping (0 dB) stay clear. The crowd
  one-shots keep their 80 ms attack.
- **Press-box commentator (`audio/mix.ts` `VoiceStage`):** HRTF on the centre line, 2 m behind and 0.8 m above the
  seat (or "above" / "overhead"), no distance loss, a 110 Hz high-pass and Blauert's directional bands as EQ (HRTF
  front/back and height are weak on most headphones). No reverb send. The same chain plays the commentary track,
  the preset answers and the live answers.
- **Mixer (`/?mix=1`, testing only):** one slider per group, the near-end amount and the commentator position, heard
  live in all three audio contexts through one shared store. Reset; Submit copies and downloads `audio-mix.json`.
  The draft is kept in localStorage and read only with `?mix=1`, so judges always hear `DEFAULT_MIX`. Submitted values
  become `DEFAULT_MIX` in `audio/mix.ts`.

## D21. Livelier commentary (`--style lively`) and a local Liverpool v Arsenal listening test (24 Oct 2026)

- **Why:** potencialbg found the commentator bland ("Midfield, far side, Reds."). Research file 48: radio commentary
  is play-by-play **and** colour, with verbs, inversion at peaks, places said naturally and evaluation after the
  outcome. radio_v1 was nearly all bare play-by-play labels.
- **`lively` template set** (`commentary/lively.py`, chosen by `build_commentary --style lively`): the same facts,
  drafts, timing, spoiler rules, truth verifier and seeded RNG as radio_v1, with commentator wording and the
  listener's side ("to your left"). The shortest fallbacks stay plain, so tight gaps still fit. The shipped judge
  track stays **radio_v1** until we decide to re-render it.
- **Real names, local only:** `--names pipeline/names/<x>.local.json` renames teams, players and venue over the
  synthetic events (`source.rename`) and writes to `web/.local/<x>/`. Both paths are git-ignored. The build refuses to
  write a renamed track into `web/public`. Only the dev server serves it (`vite.config.ts`, `apply: 'serve'`), at
  `/?names=<x>`. On the deployed site the path 404s and the shipped track plays. This keeps the CLAUDE.md rule (synthetic
  data, fictional clubs in anything we ship) while letting us hear the style with familiar names.
- **First render (24 Oct):** Liverpool v Arsenal at Anfield, squads from line-ups around 10–25 Oct 2026 (unverified),
  72 lines, truth_check 72/72, 0 spoiler leaks, 4,251 characters synthesised.
- **Not changed:** the score announcements on screen, preset answers and live Ask still use Reds and Navy.
- **lively_v2, pass by pass (24 Oct, potencialbg: "Gakpo is with the ball, moving down the left flank... cuts
  inside, passes back to Mac Allister, Mac Allister switches sides"):** every completed pass is called as it arrives
  (never earlier: the receiver is its outcome) with how it travelled ("plays it back to", "switches it to the right
  for", "out wide to"), from the event's start and end points. Between passes, a line every ~3.2 s says what the
  holder does, from B's 25 Hz ball track ("moving down the left flank", "cuts inside", "drives forward"); a player
  standing still gets where he is ("Patient from Arsenal, out on the far side in midfield"), at most twice. Flanks
  are the team's own left and right, as commentators say them. Second render: 113 lines, truth_check 113/113, 0 leaks.
- **Mix (second submission, 20:30 UTC):** crowd beds -14 dB, chants -20, reactions -7; the rest unchanged.

## D22. Press-to-interrupt, and no mid-sentence resume after an Ask (24 Oct 2026)

- **Why:** research file 49. A press is the only barge-in that can promise a stop "within a fraction of a second"
  without an open mic (voice barge-in needs Live-Reference AEC, after the deadline). And after an answer, the commentary
  track picked the cut line up mid-sentence at the playhead, which sounds broken.
- **Ask stays pressable during an answer.** Its label becomes "Stop the answer" and it keeps focus, so a screen reader
  user can double-tap it. The button or **A** stops the answer at once (preset clips, browser voice or live answer;
  a 0.1 s fade, never a click), opens the question menu and **keeps the commentary paused** for the next question.
  **Escape** stops it and goes straight back to the action. Closing the menu, or 10 s with no question, plays the
  catch-up from the moment the commentary first paused, then resumes. The next question reuses that pause: no second
  pause, and no "hold that thought" (the build-up would be paused too).
- **Restart or drop, never mid-sentence.** If the playhead moved more than 0.25 s while the voice was paused (an Ask:
  the replay clock keeps going), the cut line goes through the existing late rule: it restarts from the top while it is
  inside its `stale_ms`, otherwise it is dropped and the catch-up covers it. With today's cues (`stale_ms` 0–1.5 s for
  most lines) that means dropped. A replay pause keeps the playhead still, so that line still resumes in sync (unchanged).
- **Checked:** 12 new unit tests (9 for the Ask controller and the stoppable players, 3 for the track; 2 of the
  track tests fail on the old code), vitest 118/118, Playwright + axe 90/90, and in Chrome on the dev server: A during
  an answer opened the menu 6 ms later with focus on the first question; Escape played "Back to the action." and
  the match went on; 10 s without a question did the same.
- **Not checked:** stopping a *live* answer on the deployed relay (only the unit test with a fake live mode), and how
  the stop fade sounds by ear.

## D23. The final product UI: one screen, a match card, the test tools stay behind their flags (25 Oct 2026)

- **Why:** sighted judges score UX & Presentation (20%). The page worked, but read like a test bench: no pitch line,
  no visible match state, and the disclaimer sat where the pitch should be.
- **What:** one column (34 rem), the name and a one-line pitch, a match card (score, match clock, current chapter,
  state; `web/src/scoreboard.ts`), then Start, Ask with its shortcut hint, the status line and a row of three secondary
  buttons. The synthetic/AI-voice notice moves to the foot of the page. One accent colour, pitch green (`#0a6b4a`
  light, `#5fd3a3` dark), replacing the red that matched one team. No animation, system font, plain CSS.
- **Accessibility:** the card is a labelled section with a hidden "Match" heading, read on demand and **not** a live
  region (the clock ticks every second); score changes are still announced once through `say()`. Ask now follows
  Start in the tab order, so it's one Tab away during play. Every id, label and shortcut the tests and the tester rely
  on is unchanged. The chapter shown is the one at or before the playhead, so it never names what's coming (D11).
- **Checked:** vitest 124/124 (6 new), Playwright + axe 96/96 (a new "product view" test, 6 projects: no tester,
  mixer or debug elements at `/`, everything on one screen at desktop and phone portrait, clock and chapter update).
- **Not checked:** Narrator, TalkBack and VoiceOver with the new layout (still the manual walkthrough in REMAINING.md).

## D24. Phone pads, the listener's own mix, and the 90-minute readiness run (26 Oct 2026)

- **Why:** potencialbg, 26 Oct: the demo is for a blind fan on a phone, so the screen must work by touch and screen
  reader alone. Ask and press-to-interrupt (D22) had never been run end to end with a real voice question.
- **Two pads.** On a phone held upright (`max-width: 40rem` and `min-height: 32rem`) the page under the match card is
  two halves: **Ask the commentator** on top, **Start / Pause / Resume** below. Side by side on wider screens; Ask comes
  first in DOM, tab and reading order. Each pad's accessible name is its visible words (`.pad-label`); the icons are
  `aria-hidden`; the hint under each pad ("Tap, wait for the beep, then speak", "Pauses the match") is its
  `aria-describedby`. Before the match the Ask pad is `aria-disabled` (not `disabled`), so it can be found by touch and
  says "The match hasn't started. Start is the bottom half of the screen."
- **One press, then speak.** With live Ask on, the Ask pad asks out loud straight away (no menu); without it (no relay,
  `?live=0`) it opens the quick questions. The presets also have their own **Quick questions** button below the pads,
  and the menu gains **Back to the match** for touch users. Pressing Ask during an answer stops it (D22); with live Ask
  the commentary stays held for a next question and "Tap Ask to ask again" is announced, then 10 s later it goes back
  to the action. Ask while paused resumes the match first (the paused stage context could not play the catch-up).
  Pause during an answer or a hold stops it quietly first (`AskController.dropHold()`), so nothing resumes behind it.
- **No announcement into the open mic.** A live question shows "Listening. Speak after the beep." on screen only;
  the rising earcon is the cue. A screen reader reading a live region then would be transcribed as the question.
  `live-ask.ts` reports the phases (`heard`, `answering`) as a window event; `main.ts` shows them, visually only.
- **Press feedback.** Every pad press vibrates (Android; off when Vibration is off) and plays a 0.1 s tone straight to the
  stage context's output (rising: ask / resume; falling: stop / pause; Pause waits 120 ms so its tone is heard).
- **The listener's own mix.** The `?mix=1` mix is now saved on the device (`audio/mix.ts` `saveMix`, the same
  localStorage key as D20's draft) and played on every visit, main page included. A device with nothing saved plays
  `DEFAULT_MIX`, so a judge on a fresh browser still hears what we tuned. The mixer opens with the helper explanation
  ("Set this up once with a sighted friend or carer...") and lists the voice and crowd first. Settings links to it
  ("Fine-tune every sound, with a helper"). Submit is now "Save a copy (JSON)".
- **Relay:** an empty `incomplete` Voice Live response is retried once (seen in 1 of 4 phone runs: the question was
  transcribed, no audio came, the fan heard "Live questions aren't available"). Each golden turn now carries Voice
  Live's token `usage`, so cost per question comes from real counts.
- **Tools:** `web/tests/a/phone-e2e.mjs` (phone-sized Chromium, a fake microphone speaking a WAV, an analyser on every
  AudioContext; it measures, not guesses, whether each sound played and when it stopped) and `web/tests/a/soak.mjs`
  (one full half in real time). `pipeline/tely/eval/soak_bundle.py` builds both full halves of seed 24 into
  git-ignored `web/.local/`, with a tone in place of TTS (no Speech calls); `?bundle=soak1|soak2` plays them on the dev
  server only (`replay/base.ts`).
- **Checked (26 Oct, phone-e2e against the deployed relay, 360x640 @3x):** match start (crowd and commentary audible),
  spoken "What is the score?" answered ("Reds nil, Navy nil, 56 minutes played.", 0.8 to 1.4 s from end of speech),
  barge-in stops the answer in 65 to 155 ms, pause/resume (clock and all three contexts silent while paused, then
  carry on). 5 full runs; 1 spoken Ask failed upstream (fixed above, not yet deployed). Screens in `video/screens/`.
  vitest 124/124, Playwright + axe 96/96, relay 46/46.
- **90-minute readiness run (26 Oct, `soak.mjs`, local dev server + local relay on Voice Live, both halves at once,
  real time, 2 x 48 min of match; reports in `eval/soak/`):**
  - Both halves played to the end (playhead 0 to 2879 s). **Clock drift:** playhead against wall time -37 ms over
    35 min (half 1) and -337 ms over 38 min (half 2; the stage audio clock itself -48 ms). No fix needed.
  - **Commentary sync** (each line's first audible output against when its t_in was due): median 84 / 82 ms, 90th
    percentile 123 ms, first third 82 / 74 ms against last third 83 / 85 ms, so it does not drift. 22 of 747 lines were
    not heard: lines due during an Ask, dropped by design (D22). One line started 4.0 s late after an Ask (restart rule).
  - **Audio glitches:** no dropout over 300 ms in either half (no stage output under -94 dBFS outside the pause, the Asks
    and the offline minute). Chrome's `playoutStats` was not available, so underruns are not measured directly
    (unverified). The quietest murmur sits near -68 dBFS, about 30 dB under the commentator: that is the D20 mix.
  - **Memory:** JS heap 8 to 25 MB (max 25.1) over 49 min; DOM nodes 498 to 892 / 1315. No leak that matters for a match.
  - **Live Ask, every 10-11 min (so each one found the relay's 90 s idle close and reconnected):** 10/10 answered,
    0.88 to 3.5 s from end of speech (median 1.4 s). The 55-minute Voice Live reconnect was not reached (unverified live).
  - **Dropped connection (45 s offline):** the Ask during it got the "not available" refusal, and Ask worked again 15 s
    after the network came back. Fixed from this run: the refusal clip is now fetched while online. Before, nothing
    played in the commentator's voice offline (the browser's own voice was the fallback); after, the clip plays.
  - **Cost per question** from the 10 real token counts (about 2,600 to 4,200 tokens; 2,300 to 3,600 text in, mostly
    cached; 70 to 180 audio out) at file 27's Voice Live rates (Standard audio $0.015 / $0.026 per 1K; Standard text
    rates are not in our files, so Pro text $0.004 / $0.016 as an upper bound, and no cache discount): **$0.013 to
    $0.025, mean $0.017**. A fan who asks 10 questions costs about $0.17; the 30-question cap about $0.51.
    Commentary is rendered once per match, not per fan: a full 90-minute track is about 42,000 characters, about
    $0.92 at file 27's HD rate of $22 per 1M (text characters; how Azure counts our SSML is unverified). Static Web App
    Free and a relay that scales to zero add nothing per match.
  - The soak bundles use a tone instead of TTS, and the relay answers from the judge cut (so "56 minutes played" at any
    playhead): the run tests timing, sessions and memory, not answer content.
  - Seen in the full second half, not in the shipped cut: `spoiler_leaks` flags "Intercepted by Morani! Reds have it
    back." while the next pass is in flight (a checker false positive: the line is about the interception). Not fixed.
- **Deployed (26 Oct, after #31):** web, and relay image `6a6a0cd8ba38` (revision 11). `phone-e2e.mjs` against the live
  site at 360x640: start, spoken Ask (0.9 s), barge-in (206 ms), pause/resume and the mixer all pass. Playwright + axe
  at phone portrait against the live site: 14/16, the 2 failures were the tests assuming no relay (fixed in the
  follow-up PR). That run sent 6 tester-mode events to App Insights; `pull_feedback.py` now leaves out those codes.
- **Not checked:** TalkBack, VoiceOver and Narrator with the pads (manual); a real phone's vibration and tone; a real
  voice in a noisy room.

## D25. Three tabs (Setup, Laptop, Phone) and sound levels by voice (26 Oct 2026)

- **Why:** potencialbg, 26 Oct: one page for three audiences. A helper tunes the sound with the fan once, judges on a
  laptop need to see the keys, and the blind fan on a phone keeps the two pads. The fan should also be able to change
  any sound out loud ("reduce the whistle by 5") on a 0 to 100 scale.
- **Tabs:** a `role="tablist"` (Setup, Laptop, Phone) next to the title, with arrow keys between tabs (APG automatic
  activation). They switch the layout of one page (`main.v-setup|v-laptop|v-phone`), so the match never stops.
  Narrow screens open on Phone, others on Laptop, and `?view=` opens a given tab (a tab click writes it to the URL;
  the old `?mix=1` link opens Setup). Phone is the D24 layout unchanged. Laptop shows the pads side by side, a key
  card (Space: start or pause, Enter: ask, Esc: back to the match) and key hints under the pads. **Space and Enter
  work in every view** while focus is on a pad or on nothing; every other control keeps its own Space and Enter.
- **Setup** holds the sound desk (`tester/mixer.ts`, loaded only when the tab first opens) and the settings, which
  moved there from the Settings button. The desk has a 0 to 100 channel per sound group, with -5 and +5 buttons and
  the dB shown small. It also has four starting points, a live spectrum of the stadium output (aria-hidden, 2 fps
  under reduced motion), and the words to say for each channel. Its dark console look is the same in both themes.
- **The 0 to 100 scale** is linear in dB over -40..+12 (`audio/mix.ts levelFromDb`), so 0 is off and one step is
  about 0.5 dB. The mix is still saved in dB, so mixes saved before still load.
- **By voice:** a new Q&A tool `adjust_sound(sound, change | level)` (`qa/tools.py`, schema and MCP mirror, persona
  rule). The page sends its levels with every `ask`, and the relay passes the fan's level for that sound to the tool,
  never the model's. The commentator can then say "The whistle is now 25 out of 100." Without a level it says the
  change. The page applies the `{sound, level}` prefs to the mix, saves it, and the desk moves with it.
- **Checked:** pipeline pytest, relay pytest (new adjust_sound tests), vitest 132/132, Playwright + axe 108/108 at all
  6 projects (new: tabs, Space and Enter, the desk).
- **Not checked:** a real spoken "turn the whistle down by 5" through Voice Live (the new tool needs the relay
  redeployed first), and screen readers with the tabs.

## D26. The name is Tely (27 Oct 2026)

- **Why:** potencialbg, 27 Oct: "the name is tely and make sure that it is like this everywhere". Tely is short for
  television and teleport ("teleport to the stands"). We chose Tely over Telly, which is already a US free-TV company
  and a Czech streaming service that carries football. No other hackathon entry uses either name.
- **Said "telly".** Wherever a voice says the name, it gets the spoken form "Telly": `video/narration.py` (`SAY_AS`) and
  the tour's intro (`learn.ts`, `speech`). Captions and on-screen text keep "Tely". Never write it in capitals ("TELY"),
  because screen readers may spell it out.
- **Renamed everywhere:** the display name, the Python package (`pipeline/tely`, so `python -m tely.build_bundle`), the
  bundle formats (`tely.meta`, `tely.signals`, ...), the MCP server (`tely-qa`, header `X-Tely-Playhead`), the debug
  globals (`window.telyLive`, `window.telyCommentary`), `TELY_NO_AF`, research file 43 (`43-tely-architecture.md`),
  and the browser sound stage (class `SoundStage` in `audio/sound-stage.ts`, a name for what it is, not the product).
- **Kept on purpose:** `eval/report.json` keeps the real Foundry evaluator name and run URL (`audiostands-numeric-truth`),
  because they are the IDs of runs that happened. Azure resource names (`rg-as-judge`, `as-foundry-...`) keep "as":
  renaming them means new resources. Settings, the sound mix and tester answers move to `tely.*` keys, and each
  is still read from its old `audiostands.*` key once if the new one is empty, so nothing saved on a device is lost.
- **After merging:** reinstall the package (`pip install -e "pipeline[dev]"`), then redeploy the web app and the relay
  (`azd deploy`), so the live page says Tely (the uptime check looks for `<title>Tely</title>`) and the relay speaks
  the new MCP header. Re-render the voiceover with `python video/narration.py`.

## D27. The commentator speaks six languages (27 Oct 2026)

- **Why:** potencialbg, 27 Oct: the commentator should talk in other languages. A friend can set it in Setup, or the
  fan can ask the commentator. The languages are English, Bulgarian, Spanish, Arabic, French and German, for the
  match commentary and the live answers.
- **Match commentary:** `tely/commentary/languages.py` translates the 70 finished English lines with Foundry
  (`l10n_v1@gpt-5-mini`, strict JSON schema, keyless). It records them with Azure Speech in
  `en-US-BrianMultilingualNeural`, the same Brian in every language, inside `<lang xml:lang>`. Each line keeps the
  English line's time, evidence and checks.
  - We translate whole lines, not templates (file 35), because the English track is already verified.
  - A translation must keep every digit and player name, and must not leave an English number word. The first run
    left "Rojos nil, Azules one, sixty minutes played" in Spanish, which the check now rejects and re-asks.
  - A line longer than its slot is recorded again, faster (prosody rate, at most +45 %). That was 2 to 8 lines per
    language, with 0 overlaps.
  - Translations and the lengths of discarded recordings are cached in `commentary/l10n/<lang>.json` (committed), so
    a rebuild makes 0 model calls and 0 TTS calls.
  - The bundle grows from 5.9 MB to 15.7 MB, and the manifest lists one track per language.
- **Live answers:** a new tool `set_language(language)`. The page sends `lang` with every `ask`. The relay switches
  the Voice Live session's voice (BrianMultilingual for every language except English), its instructions (speak only
  that language, the team names in it) and its transcription language. After `set_language` mid-answer, the
  `session.update` goes out with the tool result, so the reply is already in the new language.
- **Page:** a "Commentator language" select in Setup's settings, saved on the device. The commentator's
  `set_language` changes it too, and the commentary track reloads mid-match. The line speaking stops, and nothing
  resumes mid-line.
- **Still English:** the offline preset answers, the refusal clips, the captions and the page's own words.
- **Checked:** pipeline pytest (new `test_languages.py`, `test_set_language.py`), relay pytest, vitest 138/138,
  Playwright + axe 114/114. A test render of every language came back about 2 s long.
- **Not checked:** the recordings by a native speaker of each language, and a live spoken "speak Spanish" (after the
  deploy).
- **Live check (27 Oct, after deploy):** a spoken "Please speak Spanish from now on" on the live site called
  `set_language(es)`, answered in Spanish in 0.9 s, switched the Setup select, and played 65 Spanish match lines. The
  next question went out with `lang: "es"` and was answered in Spanish. The reply was wordy ("Claro, voy a cambiar el
  idioma… De momento no haré nada más. Seguimos…"), because the model spoke before calling the tool. The persona now
  says to call `set_language` without saying anything first, then say only the tool's sentence. The first question
  after the relay had scaled to zero never reached it and fell back to the presets; the retry worked.

## D28. Ball-position answers say only what the tool says (27 Oct 2026)

- **Why:** the live check after the D26 deploy asked "Where's the ball?" at 56:34. The tool said "The ball is out of
  play." (x -53.7, behind the goal line), and the commentator added "It's sitting on the sideline for Reds, near the
  halfway point", which is made up. It also opened with "Let me check", which the hosting note already forbade.
- **Relay:** `function_call_output` no longer carries the tool result's raw `x`/`y` (`MODEL_HIDDEN` in
  `relay/voicelive.py`): the model gets the tool's words only. The golden-turn log keeps the full result for the evals.
  The tools themselves are unchanged, so the offline presets, the MCP server and the golden cases are untouched.
- **Persona:** for where the ball is, say what `get_ball_position` says, in its words, adding no side, area, distance
  or team it didn't give. The hosting note now says nothing comes before the tool result: naming "let me check"
  alone wasn't enough, the model said "I'll check the current ball position for you now" instead.
- **Checked:** relay pytest (the model's tool output has no x/y; the log still does) and pipeline pytest. Before the
  deploy, this relay run locally against real Voice Live (phone test, localhost page): "Where's the ball?" at 56:35
  got "The ball is out of play." and at 57:58 (the video's take) "Navy have it, defensive third, far side. 80 metres
  from goal.", each the tool's words exactly; "Who wins?" still got "that's for the match to decide".

## D29. Languages finished: the quick questions, Hindi, and the spoiler firewall in every language (27 Oct 2026)

- **Why:** D27 left the offline answers in English, and its truth check on translations covered digits and names but
  not spoilers. The firewall only knew English outcome words, so a translation could give a result away unnoticed.
- **The firewall in each language** (`languages.py` `OUTCOME_L10N`, `spoiler_check_l10n`): per-language regexes for
  a shot's and a pass's outcome words (stems where the language inflects; "Tor" but not "Torwart", "гол" but not
  "голям"), checked at the English line's own time with `verifier.spoiler_check`'s rules. The translator now gets a
  `reject` hook, so a line that fails is asked again (three tries, then the build fails).
  - **It found a real leak** in the shipped Arabic track: c_0004, "VAR is checking it", was translated as "VAR is
    checking **the goal**" (الهدف) 20 s before the VAR decision. Re-translated: "في الشباك... لحظة، الفار يراجعها."
  - The instructions now also say: add no outcome word the English doesn't say, and keep digits as digits (the first
    French run wrote "cinq mètres" for "5 metres", which the digit check rejects).
- **Quick questions in every language:** the 110 answer fragments are translated with the same checks and recorded in
  BrianMultilingual into `answers/<lang>/` (same `index.json` shape). `FragmentPlayer.setLanguage()` switches folder,
  and keeps the current answers if a language has none. The page switches it with the commentary.
- **Hindi** (`hi-IN`) is the seventh language: commentary, answers, live answers (`set_language`, MCP schema, persona).
  The team names are "लाल टीम" and "नीली टीम". 14 Hindi lines were re-recorded faster to fit; one (c_0022) still runs
  past the next line's start at the +45 % cap (`l10n.fits: false`).
- **Page words stay English, so the page's `lang` stays `en`** (WCAG 3.1.1: the page language is the language of its
  words; `lang="ar"` on English buttons would make a screen reader read them with an Arabic voice). What is in the
  chosen language carries its own `lang`, and Arabic also `dir="rtl"`: the picker's options and, in screen-reader
  mode (D30), each commentary line.
- **Numbers:** 7 tracks, 1,266 files, 33.8 MB. Translations: `l10n_v1@gpt-5-mini`, cached in `commentary/l10n/`.
- **Checked:** pytest (new: each language's outcome words; a leaking translation is asked again; every shipped
  translated line passes the digit/name check and the firewall in its language, with the English line's time and
  evidence; every language has all 110 answers), vitest 139/139 (new: FragmentPlayer.setLanguage).
- **Not checked:** the recordings by a native speaker of each language.

## D30. Two detail levels, screen-reader mode and one-ear mode (27 Oct 2026)

- **Why:** blind fans listen in different ways. Some want only the big moments; many run a screen reader at a speed no
  AI voice matches; some have one earbud or hear in one ear, so anything panned left or right is lost.
- **Detail level** (Setup, saved on the device; or by voice through `set_preferences detail`): **Full radio** (today's
  track) or **Key moments only**: the cues with `priority >= 3` (`lane-a` `KEY_PRIORITY`). On the judge cut that's 12 of
  70 lines: the AI notice, both build-ups, the header call, VAR, the four outcome reactions, the goal's detail and the
  yellow card. A filter on existing cues: no new words and no LLM call, so every line kept is already verified. D18's
  "one detail level" no longer holds; the old `verbosity` argument now names the two levels instead of "Done.".
- **Screen-reader mode:** the voice's own gain goes to 0 and each line goes to a polite, atomic live region
  (`#reader-lines`) when it would have started, with the line's `lang` (and `dir="rtl"` for Arabic), so the fan's
  screen reader reads it at their own speed. Lines still duck the crowd; crowd, sound icons and vibration stay. A line
  stopped before it is heard (pause, seek, Ask, language switch) is never announced, and a line resumed mid-sentence
  isn't read twice. Answers to questions are still spoken by the AI voice.
- **One-ear mode:** every AudioContext (stage, commentary, live answers) registers with `audio/mono.ts`, which sets its
  destination to 1 channel (Web Audio's "speakers" down-mix sums L and R). Where the ball is still comes through:
  the end nearest the ball lifts (D20), and every 5 s in play a soft 150 ms tone is pitched by the ball's third, seen
  from the fan's team: 262 Hz own third, 330 Hz midfield, 440 Hz attacking third (`audio/position-tone.ts`).
- **Checked:** vitest 145/145 (new: the key filter on the real cues, settings, mono on/off for late contexts, the pitch
  per third and side, the track's mute and `onLine`, and that a stopped line is never announced), pytest and relay
  pytest (the new `detail` argument), Playwright + axe on desktop and phone portrait (the controls, saved across a
  reload, axe on Settings in light and dark, and the first line reaching the live region on time).
- **Not checked:** NVDA, Narrator, TalkBack or VoiceOver reading the live region on a real device; the mono down-mix
  on a real one-ear Bluetooth earbud.
