# 46 — Using GitHub Copilot Agent Mode, GitHub CLI/SDK and Azure MCP in our build (and showing judges we did)

_Accessed/compiled: 20 Oct 2026 · Priority area: Technological Implementation (20%) hero technologies, dev workflow, submission evidence_

## TL;DR

- **The rules name these tools as hero technologies, and they say nothing about AI-assisted coding.** Technological Implementation asks "How effectively does the Project leverage the hero technologies", and the list includes "Azure MCP, GitHub Copilot Agent Mode, … GitHub SDK, GitHub CLI". There is no clause on AI coding tools. What the rules do require is that the submission is "the original work of the Entrant", and that developer tools are used under their own licence terms. So use the tools for real, then show the evidence plainly.
- **Copilot Free is enough for agent mode and MCP. The cloud agent needs a higher plan.** GitHub's plans page marks Agent mode, MCP, custom instructions and prompt files as "Included" on Free. **Copilot cloud agent** (the new name for the "coding agent" you assign issues to) is "Not included" on Free. It is included on Student, Pro ($10/month), Pro+ ($39/month) and Max. Billing moved to **GitHub AI Credits** on 1 June 2026. Verified students moved to a separate **Copilot Student** plan on 13 Mar 2026. *Team step: check which plan each of us already has. We sign up for nothing.*
- **Azure MCP Server is on npm as `@azure/mcp`, latest 3.0.0, published 12 Oct 2026.** Start it with `npx -y @azure/mcp@<ver> server start`. Useful flags are `--read-only`, repeated `--namespace X`, and `--mode namespace|consolidated|all|single`. It signs in with whatever `az login`/`azd auth login` already holds. It has the namespaces we need: `monitor` (log, metric and trace queries), `containerapps`, `cosmos`, `eventhubs`, `deploy` (`deploy app logs get` for an azd env), `speech` and `foundryextensions`. VS Code caps all MCP servers together at **128 tools**. The default namespace mode stays under that cap.
- **GitHub Models was retired on 30 Jul 2026, so it is not an option for prototyping.** Prototype straight on Microsoft Foundry. Use GitHub inside the product in two ways. First, CI publishes each **synthetic match dataset + realism report as a GitHub Release** (`gh release create`) with a signed **artifact attestation** (`actions/attest@v4`). Second, the app reads the latest release through **Octokit** so it can show its "data version".
- **Evidence for judges:** a "How we built it" README table (tool → what it did → link to PRs/screenshots), PR labels that say which assistant was involved, a CI-generated "AI-assist ledger" made with `gh`, and one 5-second Azure MCP shot in the video. Name **Claude Code** where it was used. Never credit Copilot with work it didn't do.

## Findings

### 1. What the official rules say

The rules come from `microsoft/insidethegamehackathon` (see research 12). Section 6.2 lists the hero technologies under Technological Implementation. The Multi-Agent prize text mentions "using GitHub Copilot, Microsoft Agent Framework, A2A". Section 4 says "Use of any developer tools will be subject to the license agreement related thereto." Section 4.11 allows open-source software, and §4.6 requires the submission to be "the original work of the Entrant". **No clause requires us to disclose AI-assisted coding, and none forbids it.** Our view is that honest disclosure is the safe default. Judges also can't credit Copilot use they can't see.

### 2. Copilot plans: what each feature needs (from the GitHub plans page, 20 Oct 2026)

| Feature | Free | Student | Pro / Pro+ / Max |
|---|---|---|---|
| Agent mode (IDE) | Included ("Limited") | Included | Included |
| MCP in agents | Included | Included | Included |
| Repo custom instructions, prompt files | Included | Included | Included |
| **Copilot cloud agent** (assign issue → PR) | **Not included** | Included (no third-party agents) | Included |
| Copilot code review | Only "Review selection" in VS Code | Included | Included |
| Copilot CLI | Included | Included | Included |
| Price | $0 | $0 (verified students) | $10 / $39 / $100 (Max: unverified, from secondary sources) |

- Credits: Pro includes 1,500 AI Credits a month (1,000 base + 500 flex) and Pro+ includes 7,000. The page gives no number for Free or Student.
- Since 1 Jun 2026 "all Copilot plans bill based on GitHub AI Credits consumed". **Copilot code review also uses GitHub Actions minutes.**
- New sign-ups were paused from 20 Apr 2026. Secondary sources say they reopened from 17 Jun (unverified). None of this affects us if we already hold a plan.
- Students: since 13 Mar 2026, GitHub Education students are on the **Copilot Student** plan. It sits above Free but below Pro. Premium models can't be picked by hand but are still reachable through "Auto" (secondary source). Verified teachers can still get Pro free.
- The VS Code extension for Azure MCP and the **GitHub Copilot for Azure** extension both require "a GitHub Copilot subscription", and Free counts. GitHub Copilot for Azure "includes and uses the Azure MCP Server extension" and works **in Agent mode**. The older `@azure` chat participant is no longer how the docs describe it.

### 3. Copilot features we would use

- **Agent mode (VS Code, "Local" harness):** edits files, runs terminal commands and calls MCP tools, asking approval per tool. The choices are *Current session*, *Current workspace* or *Always allow*. Checkpoints restore files and chat, but they **do not undo changes made to external services**. That is a reason to keep Azure MCP read-only.
- **Copilot cloud agent:** assign an issue to Copilot on GitHub.com, GitHub Mobile, the API or `gh`. It opens a "[WIP]" PR, works in a GitHub Actions environment, then asks for review. You iterate by @mentioning `@copilot` in PR comments, and it only listens to people with write access. Limits: it works in one repository, one branch and one PR per task, with **59 minutes per session**. It sees the issue's title, body and comments **as they were when it was assigned**. Comments added later are not seen (MS Learn module). A ruleset or branch protection that conflicts with the agent blocks it. Environment: `.github/workflows/copilot-setup-steps.yml` with a single job named exactly `copilot-setup-steps`, kept on the default branch. Copilot only honours `steps`, `permissions`, `runs-on`, `services`, `snapshot` and `timeout-minutes` (max 59). CLI: `gh agent-task create "…" --follow` (gh ≥ 2.80; latest gh is v2.102.0). Copilot can review a PR with `gh pr edit --add-reviewer @copilot` (gh ≥ 2.88).
- **Custom instructions:** `.github/copilot-instructions.md` applies to the whole repo. Path-specific rules go in `.github/instructions/NAME.instructions.md` with `applyTo:` globs, and `excludeAgent: "code-review"|"cloud-agent"` can switch a file off for one agent. On GitHub.com, path-specific files apply only to cloud agent and code review. GitHub also reads `AGENTS.md`, or a single root `CLAUDE.md`. **We already have a `CLAUDE.md`, so Copilot will read it.** Keep it consistent with the Copilot file. GitHub's own sample prompt suggests keeping instructions under 2 pages.
- **Prompt files:** `.github/prompts/*.prompt.md`, run as `/name` in chat. Frontmatter keys are `description`, `name`, `argument-hint`, `agent` (`ask`/`agent`/`plan`/custom), `model` and `tools` (use `<server>/*` for every tool on an MCP server). Variables use `${input:name}`. Prompt files run only in the Local harness.
- **`.vscode/mcp.json`:** the top-level keys are `servers`, `inputs` and an optional `sandbox` (macOS/Linux only). Stdio servers use `type`, `command`, `args`, `env`, `envFile` and `cwd`. HTTP servers use `type: "http"`, `url`, `headers` and `oauth`. Inputs are referenced as `${input:id}`. Portable files use `mcpServers` instead, so don't copy configs between the two formats without checking.

### 4. Azure MCP Server

- **Install:** use the VS Code extension `ms-azuretools.vscode-azure-mcp-server` (it auto-updates), or the manual `npx -y @azure/mcp@latest server start`. Other routes are `dotnet tool install Azure.Mcp`, `uvx --from msmcp-azure azmcp server start`, and the image `mcr.microsoft.com/azure-sdk/azure-mcp`. The README says "Azure MCP Server 2.0 is now generally available", and npm now has 3.0.0 (12 Oct). **Pin a version.** 3.0.0 is a new major only 8 days old, so fall back to 2.0.5 (10 Jul) if a flag misbehaves.
- **Auth:** it uses the Azure Identity SDK and picks up `az login`, `azd`, VS Code or Visual Studio credentials. It never stores tokens itself. What the tools can do is limited by our own RBAC roles, so a Reader role means read-only in practice.
- **Server flags** (from `azmcp-commands.md`):
  - `--read-only` filters out every tool that isn't read-only.
  - `--namespace` can be repeated.
  - `--mode` is `namespace` (the default: one tool per service, "to … prevent VS Code from hitting the 128 tool limit"), `consolidated`, `all` or `single`.
  - `--tool` picks individual tools and can't be combined with `--namespace`.
  - `--transport` is `stdio`; `http` only works in the Docker build.
  - The `--dangerously-*` flags should never be used.
- **Commands that fit our ops:**
  - `monitor workspace log query` and `monitor resource log query` (KQL), `monitor traces query run`, `monitor metrics query`
  - `containerapps list`
  - `cosmos database container item query`
  - `eventhubs namespace get`
  - `deploy app logs get --azd-env-name` and `deploy pipeline guidance get`
  - `resourcehealth availability-status get`, `bicepschema get`, `pricing get`, `quota usage check`
  - `speech stt recognize` and `speech tts synthesize`. **TTS is tagged not-read-only, so `--read-only` hides it.**
- **Cloud agent + Azure MCP:** `azd coding-agent config` creates a user-assigned managed identity with the **Reader** role and stores its IDs in the repo's GitHub environment. It pushes a `copilot-setup-steps` branch for you to merge. You paste an `mcpServers` JSON snippet under *Settings → Copilot → Cloud agent → MCP configuration*. Tip from the docs: say "Azure" in the issue so the agent actually reaches for the Azure tools. *Team step: this needs our Azure subscription and a Student/Pro plan.*

### 5. GitHub CLI / SDK / Actions inside the product

- `gh release create [<tag>] [<files>…]` takes `--title`, `--notes-file`, `--generate-notes`, `--prerelease`, `--verify-tag` and `--latest=false`. Add a display label with `file#Label`. In Actions, set `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` (the documented pattern). Releases need `contents: write` (unverified: the REST page we fetched didn't state the base permission).
- **Artifact attestations:** `actions/attest@v4` with `subject-path`, and permissions `id-token: write`, `attestations: write` and `contents: read`. Anyone can check one with `gh attestation verify file --repo OWNER/REPO`, which checks signed SLSA provenance. For us this proves *"this synthetic dataset was produced by this workflow from this commit"*. That backs the "synthetic data only" rule and Realism Bench (E).
- **Octokit** (`npm install octokit`, v5.0.5, MIT): `new Octokit()` → `octokit.rest.*` / `octokit.request`. Public repo reads work without a token, but unauthenticated calls are rate-limited (we hit "API rate limit exceeded" while researching), so cache the result server-side.
- **GitHub Models: retired.** The playground, catalog, inference API and BYOK were all switched off on 30 Jul 2026. GitHub points to Microsoft Foundry instead. Don't mention GitHub Models anywhere in our submission.

### 6. How past winners documented AI-assisted development

We found **no primary source** of a Microsoft hackathon winner documenting Copilot/agent-assisted development (searched 20 Oct; research 13 has none either). The OmniPitch competitor repo (research 16) claims a lot and measures nothing. Our advantage is to show *measured* evidence (PR links, a ledger, screenshots) and to avoid adjectives.

## So what for us

**Tely. The pipeline stages these tools touch:** Ingest (seeded synthetic match), Interpret (tension/momentum signal, research 23/09), Explain (look-ahead commentator), Render (Web Audio crowd bed, ducking, haptics, research 27), Personalise (voice Q&A, club, language). Copilot and Azure MCP are *build-time* tools. GitHub Releases, attestations and Octokit are *product* features on the Ingest/data side.

**One-week plan for 2 people (20–27 Oct)**

| Who / what | Tasks | Why this split |
|---|---|---|
| **Copilot cloud agent** (issues, needs Student/Pro) | Well-specified, test-checkable chunks: `tension→gain/filter` mapping as a pure function with tests. The haptic pattern table (Vibration API arrays) with tests. Bicep for Web PubSub/ACA from AVM (research 30). The GitHub Actions release workflow. README accessibility section draft. Unit tests for the Stats MCP tools. | Runs in parallel while we build the hard parts, and leaves a PR trail judges can read |
| **Copilot agent mode** (local) | Scaffolding the Web Audio graph modules (crowd bed, chant layer, ducking bus). Wiring the MCP client in Agent Framework. Fixing failing tests. Using **Azure MCP** for "why is the replay slow?" questions | Interactive, fast feedback, and Azure context without leaving the editor |
| **Humans** | Commentator look-ahead logic and prompts, the sound design (ear-tested with screen reader on), voice Q&A latency tuning, the demo video, final review of every PR | Taste, accessibility judgment and accountability can't be delegated |

**Quality rules**
1. Commit the instructions file and path-specific rules below on day 1.
2. CI runs `pytest` + `vitest` + Bicep build on every PR, and no PR is merged red.
3. Every Copilot PR gets a human review, plus `gh pr edit --add-reviewer @copilot` when we have the credits.
4. Keep the Azure MCP Server `--read-only` in `.vscode/mcp.json`. Do writes through `azd` ourselves.
5. Issues for the cloud agent use the template below, with acceptance tests written *before* assigning.

**Azure MCP use during the week:** ask Copilot things like "List Container Apps in rg-tely-judge and their latest revision". Or "Query App Insights traces for the last hour where `tools/call get_tension` took over 300 ms". Or "Show `azd` app logs for env judge". Take **one screenshot** of a real answer for the README.

**Our own Stats/Audio MCP server** (research 18) goes into the same `mcp.json`. Copilot agent mode can then call `get_tension(match_id, clock)` while writing the crowd-mix code. One server, two consumers (the product's agents and the dev tools), which is a good "MCP integration" story.

**Honesty (this file was researched by Claude, via Claude Code).** If the team also writes code with Claude Code:
- Keep its `Co-Authored-By: Claude …` commit trailers.
- Label those PRs `ai:claude-code`.
- In the README, write e.g. "Research and parts of the stats engine were drafted with Claude Code (Anthropic); Copilot agent mode was used for X; Copilot cloud agent opened PRs #12, #15, #19; all were reviewed and merged by us."
- Never write "built with Copilot" for code Copilot didn't write. The hero-tech credit needs *real* Copilot usage, so route some real tasks through it.

**Other ideas:** the same workflow serves TwinCast (A; Bicep, CV job tests), Realism Bench (E; release + attestation is its core deliverable) and Graphics Desk (F).

**Video (under 2 min):** spend no more than 5–8 s on build tooling. One shot: Copilot agent mode answering from Azure MCP, then a flash of the PR list filtered by `ai:copilot-cloud`. Judges score the experience mainly, and research 14 covers that.

## Reuse: code & links

**`.github/copilot-instructions.md` (draft, under 2 pages)**
```markdown
# Tely — Copilot instructions
Audio-first match experience for blind/low-vision fans. SYNTHETIC match data only — never add real
Premier League data, names, crests, chants or copyrighted audio.

## Stack
- Python 3.12: simulator, stats engine, Stats MCP server (`mcp` SDK v2: `from mcp.server import MCPServer`),
  Agent Framework agents. Tests: `pytest -q`.
- TypeScript (Vite): Web Audio front end in `web/`. Tests: `npm test` (vitest). Lint: `npm run lint`.
- Infra: Bicep in `infra/` deployed with `azd`. Validate with `az bicep build -f infra/main.bicep`.

## Rules
- Numbers shown or spoken to users come from the stats engine/MCP tools, never invented by an LLM.
- Every cue follows `schemas/cue.schema.json` (cue_id, match_clock, tc_in, ttl_ms, metric, text per
  audience, evidence ids, source, truth_check). Update the schema test if you change it.
- Audio: one shared AudioContext; never start audio without a user gesture; ducking via GainNode ramps
  (`setTargetAtTime`), no abrupt gain jumps; respect `prefers-reduced-motion` for haptics.
- Accessibility: every visual element has an aria-live/text equivalent; test with keyboard only.
- No secrets in code. Azure auth is managed identity / DefaultAzureCredential.
- Keep PRs small; add or update tests in the same PR; explain trade-offs in the PR description.
```

**`.github/instructions/webaudio.instructions.md`**
```markdown
---
applyTo: "web/src/audio/**/*.ts"
---
Keep DSP mapping (tension → gain/cutoff) as pure functions in `mapping.ts` with unit tests;
AudioNode wiring lives in `graph.ts`. No `any`. Target latency budget: commentary ducking within one ramp.
```

**`.vscode/mcp.json`**
```json
{
  "inputs": [
    { "type": "promptString", "id": "azure-sub", "description": "Azure subscription ID (dev)" }
  ],
  "servers": {
    "azure": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@azure/mcp@3.0.0", "server", "start", "--read-only",
               "--namespace", "group", "--namespace", "monitor", "--namespace", "containerapps",
               "--namespace", "cosmos", "--namespace", "eventhubs", "--namespace", "deploy",
               "--namespace", "resourcehealth", "--namespace", "bicepschema"],
      "env": { "AZURE_SUBSCRIPTION_ID": "${input:azure-sub}" }
    },
    "tely-stats": {
      "type": "http",
      "url": "http://localhost:8765/mcp"
    }
  }
}
```
(Run `az login` first. Start the Stats MCP server locally with `uv run python -m tely.mcp_server`.)

**`.github/prompts/new-crowd-layer.prompt.md`**
```markdown
---
description: Add a new crowd audio layer driven by a Stats MCP metric
agent: agent
tools: ["tely-stats/*", "azure/*"]
argument-hint: "layer name and metric, e.g. 'groan on shot_saved'"
---
Create a crowd layer for ${input:layer}. Call `tely-stats` to inspect the metric's range on seed 42,
add a pure mapping in web/src/audio/mapping.ts with vitest cases at min/mid/max, wire it in graph.ts,
then run `npm test`. Follow [the web audio rules](../instructions/webaudio.instructions.md).
```

**`.github/workflows/copilot-setup-steps.yml`**
```yaml
name: "Copilot Setup Steps"
on:
  workflow_dispatch:
  push:    { paths: [.github/workflows/copilot-setup-steps.yml] }
  pull_request: { paths: [.github/workflows/copilot-setup-steps.yml] }
jobs:
  copilot-setup-steps:          # exact name required
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v7
        with: { node-version: "20", cache: "npm", cache-dependency-path: web/package-lock.json }
      - run: npm ci --prefix web
      - uses: actions/setup-python@v6   # check current major
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
```

**`.github/ISSUE_TEMPLATE/copilot-task.yml`**
```yaml
name: Copilot task
description: A small, testable task for Copilot cloud agent
title: "[copilot] "
labels: ["ai:copilot-cloud"]
body:
  - type: markdown
    attributes: { value: "Write the acceptance tests first. Copilot only sees this text as it is at assignment." }
  - type: dropdown
    id: stage
    attributes: { label: Pipeline stage, options: [Ingest, Interpret, Explain, Render, Personalise, Infra, Docs] }
    validations: { required: true }
  - type: textarea
    id: goal
    attributes: { label: Goal, description: "One paragraph. Mention 'Azure' if it touches Azure resources." }
    validations: { required: true }
  - type: textarea
    id: files
    attributes: { label: Files to touch / not touch }
  - type: textarea
    id: acceptance
    attributes: { label: Acceptance criteria, value: "- [ ] `pytest -q` passes\n- [ ] `npm test` passes\n- [ ] " }
    validations: { required: true }
```
Assign it with the web UI, `gh agent-task create "…" --follow`, or `gh issue edit 12 --add-assignee @copilot`. The exact `@copilot` assignee syntax is unverified, so check `gh issue edit --help`.

**Release + attestation of the synthetic dataset (`.github/workflows/dataset-release.yml`)**
```yaml
name: dataset-release
on:
  push: { tags: ["data-v*"] }
permissions: { contents: write, id-token: write, attestations: write }
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with: { python-version: "3.12" }
      - run: pip install -e .
      - run: python -m tely.sim --seeds 1-20 --out dist/ && python -m tely.realism --in dist/ --report dist/realism_report.html
      - uses: actions/attest@v4
        with: { subject-path: "dist/*.jsonl.gz" }
      - name: Publish GitHub Release
        env: { GH_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
        run: |
          gh release create "$GITHUB_REF_NAME" dist/*.jsonl.gz \
            "dist/realism_report.html#Realism report" \
            --title "Synthetic matches $GITHUB_REF_NAME" --notes-file dist/RELEASE_NOTES.md --verify-tag
```
Anyone can verify: `gh attestation verify match_seed_7.jsonl.gz --repo OWNER/tely`.

**Octokit in the product (show the data version in the UI / About page)**
```ts
import { Octokit } from "octokit";
const octokit = new Octokit();                       // public read; cache result server-side
const { data } = await octokit.rest.repos.getLatestRelease({ owner: "OWNER", repo: "tely" });
export const dataVersion = { tag: data.tag_name, url: data.html_url, published: data.published_at };
```

**AI-assist ledger for the README (CI or local)**
```bash
for l in ai:copilot-cloud ai:copilot-agent ai:claude-code human; do
  printf "%s\t%s\n" "$l" "$(gh pr list --state merged --label "$l" --limit 500 --json number --jq length)"
done
```

**README "How we built it" skeleton**
```markdown
## How we built it
| Tool | What it actually did | Evidence |
|---|---|---|
| GitHub Copilot agent mode (VS Code) | Scaffolded Web Audio graph, fixed tests, queried Azure via Azure MCP | PRs labelled `ai:copilot-agent`, screenshot |
| GitHub Copilot cloud agent | N issues → N PRs (mapping tests, Bicep, release workflow) | [PR list](…/pulls?q=label%3Aai%3Acopilot-cloud) |
| Azure MCP Server (read-only) | Log/trace queries, Container Apps and Cosmos checks during debugging | `docs/img/azure-mcp.png` |
| GitHub CLI + Actions | Dataset releases with signed attestations; Copilot review requests | Releases page, `gh attestation verify` |
| Octokit | App shows the dataset release it runs on | `web/src/dataVersion.ts` |
| Claude Code (Anthropic) | Research library and parts of the stats engine | commits with `Co-Authored-By: Claude` |
All AI-assisted changes were reviewed, tested and merged by the team.
```

## Sources

- Inside the Game Hackathon OFFICIAL RULES — https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md — accessed 20 Oct 2026
- GitHub Copilot plans — https://docs.github.com/en/copilot/get-started/plans — accessed 20 Oct 2026
- Updates to GitHub Copilot for students (13 Mar 2026) — https://github.blog/changelog/2026-03-13-updates-to-github-copilot-for-students — accessed 20 Oct 2026
- Student Developer Pack + Copilot Student FAQ — https://github.com/orgs/community/discussions/111352 — accessed 20 Oct 2026
- Student plan model changes (secondary) — https://roboin.io/article/en/2026/03/13/github-copilot-student-plan-removes-direct-access-to-premium-models/ — accessed 20 Oct 2026
- Updates to GitHub Copilot billing and plans (AI Credits, 29 May 2026) — https://github.blog/changelog/2026-05-29-updates-to-github-copilot-billing-and-plans — accessed 20 Oct 2026
- Copilot sign-up reopening (secondary, unverified) — https://tech-insider.org/ie/github-copilot-signup-freeze-2026/ — accessed 20 Oct 2026
- Add repository custom instructions — https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions — accessed 20 Oct 2026
- Kick off a task with Copilot agents (entry points) — https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/create-a-pr — accessed 20 Oct 2026
- Use Copilot cloud agent on GitHub — https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-on-github — accessed 20 Oct 2026
- Use Copilot cloud agent from the CLI (`gh agent-task`) — https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-from-cli — accessed 20 Oct 2026
- About Copilot cloud agent (limits, 59-min sessions) — https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent — accessed 20 Oct 2026
- Customize the cloud agent environment (`copilot-setup-steps.yml`) — https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-environment — accessed 20 Oct 2026
- MS Learn: Assigning, tracking and troubleshooting Copilot coding agent tasks — https://learn.microsoft.com/en-us/training/modules/github-copilot-code-agent/3-assign-track-troubleshoot-copilot-code-agent-tasks — accessed 20 Oct 2026
- Request Copilot code review from GitHub CLI — https://github.blog/changelog/2026-03-11-request-copilot-code-review-from-github-cli/ — accessed 20 Oct 2026
- VS Code: MCP servers — https://code.visualstudio.com/docs/copilot/customization/mcp-servers — accessed 20 Oct 2026
- VS Code: MCP configuration reference — https://code.visualstudio.com/docs/agents/reference/mcp-configuration — accessed 20 Oct 2026
- VS Code: Prompt files — https://code.visualstudio.com/docs/copilot/customization/prompt-files — accessed 20 Oct 2026
- VS Code: Chat / agents — https://code.visualstudio.com/docs/copilot/chat/chat-agent-mode — accessed 20 Oct 2026
- What is the Azure MCP Server? — https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/overview — accessed 20 Oct 2026
- Azure MCP Server with VS Code — https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/get-started/tools/visual-studio-code — accessed 20 Oct 2026
- Connect Copilot cloud agent to Azure MCP Server (`azd coding-agent config`) — https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/how-to/github-copilot-cloud-agent — accessed 20 Oct 2026
- Azure MCP Server README — https://github.com/microsoft/mcp/blob/main/servers/Azure.Mcp.Server/README.md — accessed 20 Oct 2026
- Azure MCP CLI command reference (`azmcp-commands.md`) — https://github.com/microsoft/mcp/blob/main/servers/Azure.Mcp.Server/docs/azmcp-commands.md — accessed 20 Oct 2026
- npm `@azure/mcp` (versions/dates via `npm view`) — https://www.npmjs.com/package/@azure/mcp — accessed 20 Oct 2026
- Get started with GitHub Copilot for Azure — https://learn.microsoft.com/en-us/azure/developer/github-copilot-azure/get-started — accessed 20 Oct 2026
- GitHub Models docs (retirement notice) — https://docs.github.com/en/github-models/use-github-models/prototyping-with-ai-models — accessed 20 Oct 2026
- GitHub Models is now retired (30 Jul 2026) — https://github.blog/changelog/2026-07-30-github-models-is-now-retired/ — accessed 20 Oct 2026
- gh release create — https://cli.github.com/manual/gh_release_create — accessed 20 Oct 2026
- gh attestation verify — https://cli.github.com/manual/gh_attestation_verify — accessed 20 Oct 2026
- Use artifact attestations — https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations — accessed 20 Oct 2026
- Use GITHUB_TOKEN with GitHub CLI in workflows — https://docs.github.com/en/actions/tutorials/authenticate-with-github_token — accessed 20 Oct 2026
- REST API: Releases — https://docs.github.com/en/rest/releases/releases — accessed 20 Oct 2026
- octokit.js — https://github.com/octokit/octokit.js — accessed 20 Oct 2026
- Syntax for issue forms — https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms — accessed 20 Oct 2026
- GitHub CLI latest release (v2.102.0) — https://github.com/cli/cli/releases/latest — accessed 20 Oct 2026
