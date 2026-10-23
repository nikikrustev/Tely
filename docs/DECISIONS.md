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

potencialbg tested the Voice Live playground in project `audiostands` (resource `as-foundry-stoynev`, Sweden Central) on our
free account: it heard the question and answered by voice. The playground lists models by price tier (Pro / Standard / Lite)
without version numbers. We use **GPT Realtime Mini (Standard)**, which matches `gpt-realtime-mini` in our quota list (40)
and the plan's `gpt-realtime-2.1-mini`. The exact version behind the name is (unverified). Avoid the Pro models, which cost more.

## D9. Stage 3 commentary: what we verified and what we chose (21 Oct 2026)

Built against B's hand-written 90 s sample (`contracts/b/sample/`), because Stage 1 has not merged. Every Stage 3 reader
goes through `audiostands.commentary.source.load_match()`. Switching to the real cut is one line in `MATCH_DIRS`.

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
- **Replay keeps the bundle deterministic.** `DIRECTOR=foundry` records every reply to `pipeline/audiostands/agents/recorded/judge.json`
  (features, raw reply, latency, tokens; no keys or audio). Without `DIRECTOR` set, `build_bundle` replays that file, so a rebuild,
  CI, or Nikolay gets the same plans with no Azure. If B's match changes, the replay no longer matches, those windows fall back to
  rules, and a test fails, asking for a re-record.
- **Tracing:** a workspace-based Application Insights `appi-as-judge` + Log Analytics `log-as-judge` (1 GB/day cap) were added to
  `infra/` and provisioned with `azd provision`. The connection string lives only in the git-ignored azd env.
  `configure_azure_monitor()` + `enable_instrumentation()` (file 18 §5); prompt text isn't captured. Verified with a Log
  Analytics query: `workflow.run`, `executor.process director|commentator|verifier|tts`, `invoke_agent Director`, `chat gpt-5-mini`
  under service `audiostands-director`. The App Insights resource is not linked to the Foundry project, so the Foundry "Traces"
  tab stays empty (manual step if we want it there).
- **Seen in the traces:** each new `DefaultAzureCredential` first probes the managed-identity endpoint on a laptop (~1 s per
  token fetch) before it uses the az login. The token is then cached, and the real-time harness opens connections with one
  untimed warm-up call.
- **Numeric truth on Foundry:** the same `grade()` from file 18 ran as a code-based custom evaluator (preview,
  `beta.evaluators.create_version` + an OpenAI-style eval run): `audiostands-numeric-truth`, 4/4 items passed, matching the local grader.
- **Real-time latency (`python -m audiostands.eval --realtime`):** plan → verify → TTS per build-up, from the moment the shot
  enters the look-ahead to the moment its MP3 exists, against D − lead_s. Wall clock, 1 run: 2/2 within budget, 3.75 s each.
  Waits ÷10, 5 runs: 10/10 within budget (5.8–6.0 s), p50 2.98 s, p95 3.56 s (plan p95 2.41 s, TTS p95 1.64 s). Each run opens
  its connections with one untimed warm-up call. The cold first call on 23 Oct took 6.2 s, which alone would miss the budget,
  so a live service must warm up before kick-off.
- **Skipped (BUILD_PLAN "optional, only if < 3 h used"):** LLM colour lines. The stage took longer than 3 h, so every spoken line
  stays a template, and the report says "LLM lines: 0".
- **A/B listen still to do (potencialbg):** rules vs Director differ only in the two build-ups' wording ("this could open up!" →
  "here's a chance!"; "Reds coming... Orlani... space opening up!" → "Reds... Orlani... danger!") and the hold. Record the pick here.
