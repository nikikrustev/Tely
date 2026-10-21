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
