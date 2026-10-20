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
