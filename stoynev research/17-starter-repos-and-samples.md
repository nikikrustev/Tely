# 17 — Starter repos, templates and sample code to fork

_Accessed/compiled: 20 Oct 2026 · Priority area: build/tech (repo bootstrap, Azure IaC, reusable football and overlay code)_

## TL;DR

- **There is no single `azd` template for our pipeline.** None of the 343 templates in the Awesome azd gallery uses Web PubSub. We searched its tags, titles and descriptions in `templates.json`. The Event Hubs templates are all Functions triggers. So we **build our own `azure.yaml` + Bicep**, and borrow from three living templates: `openai-chat-app-quickstart` (ACA + Azure OpenAI with managed identity), `rag-postgres-openai-python` (FastAPI + React on ACA, user-assigned identity) and `get-started-with-ai-agents` (FastAPI + Vite/React/TS + Foundry, `azd up` in 7–15 min).
- **For resources no template covers, use Azure Verified Modules (AVM).** These are the Event Hubs namespace, Web PubSub, ACA jobs, Static Web Apps and Cosmos DB. Every module exists in `Azure/bicep-registry-modules` (MIT). The Web PubSub module supports `disableLocalAuth: true`, so there are no keys.
- **Static Web Apps (SWA) only hosts the TypeScript front end.** Its managed Functions are HTTP-only, have no managed identity, and run at most Python 3.10. Linking a Container App as the API needs the Standard plan, and SWA `/api` does not pass WebSockets. So the browser gets a Web PubSub token from the ACA worker and connects to Web PubSub directly.
- **Many well-known starters are archived.** The `todo-*` blueprints, `fastapi-on-azure-functions`, `openai-chat-backend-fastapi`, `mcp-container-ts` and `mcp-sdk-functions-hosting-python` are all read-only now. Copy patterns from them, but don't fork them.
- **Football and overlay code is mostly safe to use (MIT/BSD/Apache).** Watch out for these: `unravelsports` is MPL-2.0, which is file-level copyleft. `CasparCG/server`, `k4kfh/casparcg-html-templates` and `DistroAV` are GPL. `ograf-studio` is AGPL. `react-soccer-lineup`, `roboflow/notebooks`, `immament/football-match-viewer`, `python-mcp-demos` and `functions-quickstart-python-azd-eventhub` have no LICENSE file that GitHub can detect.

## Findings

Stars are rounded. "Last push" is GitHub `pushed_at`. All values were read via the GitHub API on 20 Oct 2026.

### Azure azd templates (Python + TS on ACA / SWA / Foundry)

| Repo | What we'd take | Licence · stars · last push | One `azd up`? · keyless? |
|---|---|---|---|
| [Azure-Samples/openai-chat-app-quickstart](https://github.com/Azure-Samples/openai-chat-app-quickstart) | Smallest ACA + Azure OpenAI Bicep (`infra/aca.bicep`, `core/`), devcontainer, Quart streaming | MIT · 250 · 2026-10-09 | Yes · **managed identity by default** (README) |
| [Azure-Samples/rag-postgres-openai-python](https://github.com/Azure-Samples/rag-postgres-openai-python) | FastAPI backend + React/FluentUI front end in one ACA app; `evals/`, `locustfile.py`; one AVM module | MIT · 507 · 2026-10-19 | Yes · user-assigned MI |
| [Azure-Samples/get-started-with-ai-agents](https://github.com/Azure-Samples/get-started-with-ai-agents) | FastAPI (`src/api`) + Vite/React/TS (pnpm) front end, Foundry project + tracing, `preup` env-validation hook | MIT · 376 · 2026-10-08 | Yes, "7–15 minutes" · MI |
| [Azure-Samples/get-started-with-ai-chat](https://github.com/Azure-Samples/get-started-with-ai-chat) | Same family, chat only (optional AI Search) | MIT · 282 · 2026-10-14 | Yes, "5–20 minutes" · MI |
| [Azure-Samples/azure-search-openai-demo](https://github.com/Azure-Samples/azure-search-openai-demo) | Too heavy (AI Search RAG). Copy its `azure.yaml` **`prebuild` hook that builds the TS front end into the Python container** | MIT · 7.8k · 2026-10-15 | Yes · MI |
| [pamelafox/simple-fastapi-container](https://github.com/pamelafox/simple-fastapi-container) | Hello-world FastAPI on ACA; the cleanest Dockerfile + `infra/api.bicep` to start the worker from | MIT · 33 · 2025-07-28 (quiet) | Yes · uses Key Vault |
| [Azure-Samples/azd-ai-starter-basic](https://github.com/Azure-Samples/azd-ai-starter-basic) | Foundry project via the `azd ai agent` extension | MIT · 16 · 2026-07-10 | Yes (unverified) |
| [Azure-Samples/functions-quickstart-python-azd-eventhub](https://github.com/Azure-Samples/functions-quickstart-python-azd-eventhub) | Event Hubs Bicep with MI role assignments (we use an ACA consumer, not Functions) | **no licence file** · 0 · 2026-05-28 | Yes · MI, VNet |
| [Azure-Samples/todo-python-mongo-swa-func](https://github.com/Azure-Samples/todo-python-mongo-swa-func) | **Archived.** Still the best example of `host: staticwebapp` + a `prepackage` hook that writes `VITE_*` env from Bicep outputs | MIT · 43 · archived | — |

Gallery facts: `templates.json` lists 343 templates. 109 are tagged `managedidentity`, 77 `aca`, 12 `eventhub`, 11 `swa` and 20 `mcp`. None is tagged or described as Web PubSub. The only "real-time dashboard" entries are C# (`signalr-ai-streaming`, `GameLeaderboard`) or Fabric-based (`real-time-intelligence-operations-solution-accelerator`).

`azure.yaml` service hosts in the current schema include `containerapp`, `staticwebapp`, `function`, `appservice`, `aks` and several `azure.ai.*` / `microsoft.foundry` hosts. The schema's examples list **no ACA *job* host**. So the render and CV jobs are created in Bicep, and their images are pushed by a hook or CI (unverified that azd has no job support elsewhere). The current azd release is `azure-dev-cli_1.36.0` (15 Oct 2026).

**Static Web Apps limits (official docs):**
- Managed Functions are "HTTP only", have no managed identity, and support Python 3.8–3.10 only.
- "Bring your own APIs is only available in the Azure Static Web Apps Standard plan."
- "Only HTTP requests are supported for APIs. WebSocket, for example, is not supported."
- An API request can run for at most 45 seconds.

### Web PubSub and Event Hubs samples

- [Azure/azure-webpubsub](https://github.com/Azure/azure-webpubsub) is MIT, has 144 stars and was last pushed 2026-10-16. Its `samples/python` folder was last committed 2026-09-16.
  - `python/chatapp-microsoft-entra-id` shows **every credential type, including system- and user-assigned managed identity** (Flask). This is our keyless reference.
  - `python/pubsub-groups` is a bidirectional group client. Gotcha: `groups.py` has a stray `from torch import true_divide`. Delete that line before copying, or it pulls in PyTorch.
  - `javascript/scoreboard` is a "Real-time Scoreboard" live demo (closest to a live match dashboard), but it uses a **connection string**.
  - `javascript/relay-for-ai-agents` and `chatapp-reliable-subprotocol` are also worth a look.
  - Local development uses the `awps-tunnel` tool.
- The Python SDK `azure-messaging-webpubsubservice` has `get_client_access_token(user_id=, roles=, minutes_to_expire=60, groups=)`. Its `groups=` argument "Groups that the connection will join when it connects" lets us put a fan into `audience:casual` / `club:ARS` without a group-join round trip. We checked this in the SDK source.
- Event Hubs Python send/receive samples and the local emulator are already covered in 01. We don't repeat them here.

### Agent Framework and MCP

| Repo | Use | Licence · stars · last push |
|---|---|---|
| [microsoft/agent-framework](https://github.com/microsoft/agent-framework) | `python/samples/01-get-started` … `05-end-to-end`; `02-agents/mcp/agent_as_mcp_server.py`; `04-hosting/mcp` (`mcp_to_run` / `mcp_from_run` adapters); `02-agents/devui` | MIT · 14.2k · 2026-10-19 (release python-1.22.0, 15 Oct) |
| [microsoft/Agent-Framework-Samples](https://github.com/microsoft/Agent-Framework-Samples) | Notebook tour; slowing down | MIT · 386 · 2026-06-28 |
| [Azure-Samples/python-ai-agent-frameworks-demos](https://github.com/Azure-Samples/python-ai-agent-frameworks-demos) | Small runnable agent demos (GitHub Models / Azure) | MIT · 338 · 2026-10-19 |
| [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | **Official SDK.** v2 (v2.3.0, 2 Oct) renamed the server class to `MCPServer`; `streamable_http_app()` returns an ASGI app; `TransportSecuritySettings` sets allowed hosts and origins. v1 line still gets releases (v1.30.0) | MIT · 24.6k · 2026-10-17 |
| [PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp) | Higher-level alternative | Apache-2.0 · 28k · 2026-10-19 |
| [Azure-Samples/python-mcp-demos](https://github.com/Azure-Samples/python-mcp-demos) | FastMCP over HTTP on ACA via azd, with Agent Framework and LangChain clients, Keycloak auth | **no licence file** · 183 · 2026-10-19 |
| [Azure-Samples/remote-mcp-functions-python](https://github.com/Azure-Samples/remote-mcp-functions-python) | Remote MCP on Functions, `azd up` | MIT · 126 · 2026-10-13 |

### Football open-source code

| Repo | Use for us | Licence · stars · last push |
|---|---|---|
| [andrewRowlinson/mplsoccer](https://github.com/andrewRowlinson/mplsoccer) | Pitch drawing, heatmaps, animations for README/report images and Realism Bench plots | MIT · 550 · 2026-09-14 |
| [PySport/kloppy](https://github.com/PySport/kloppy) | Standard event/tracking model. v3.19.1 serializers cover Metrica, SkillCorner, Tracab, StatsBomb and others. **No CDF serializer found** in the tree | BSD-3 · 565 · 2026-10-17 |
| [ML-KULeuven/socceraction](https://github.com/ML-KULeuven/socceraction) | SPADL + VAEP/xT (see 08) | MIT · 819 · 2026-10-18 |
| [floodlight-sports/floodlight](https://github.com/floodlight-sports/floodlight) | Distances, velocities, accelerations and pitch overlays (Speed Trap maths) | MIT · 133 · 2026-05-04 |
| [Alek050/databallpy](https://github.com/Alek050/databallpy) | Event↔tracking synchronisation (Needleman–Wunsch), pressure, simple xG | MIT · 106 · 2026-10-16 |
| [FoTD/LaurieOnTracking](https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking) | Pitch control and Metrica viz reference code; dormant | MIT · 362 · 2022-11-03 |
| [soccermatics/Soccermatics](https://github.com/soccermatics/Soccermatics) (course at soccermatics.readthedocs.io) · [FoTD/SoccermaticsForPython](https://github.com/Friends-of-Tracking-Data-FoTD/SoccermaticsForPython) | Teaching code (xG, passing networks) · also `soccermatics/describePlayer` (MIT), which describes players with ChatGPT and is prior art for Explain | MIT · 95 / 428 · 2026-01 / 2022 |
| [UnravelSports/unravelsports](https://github.com/UnravelSports/unravelsports) | GNN graphs from tracking data | **MPL-2.0** · 249 · 2026-01-16 |
| [martineastwood/penaltyblog](https://github.com/martineastwood/penaltyblog) | Dixon-Coles/Poisson match models and Elo/Pi ratings (Called It priors) | MIT · 242 · 2026-10-19 |
| [probberechts/d3-soccer](https://github.com/probberechts/d3-soccer) | **TS front end:** d3 pitch, heatmap, action layers. npm `d3-soccer` 0.2.0. GitHub reports BSD-3 but `package.json` says MIT | BSD-3/MIT · 78 · 2025-03-03 |
| [giustini/react-soccer-lineup](https://github.com/giustini/react-soccer-lineup) | React line-up pitch. `package.json` says MIT, but there is no LICENSE file | MIT? · 58 · 2026-10-17 |

Three.js football demos: nothing is worth forking. The best one, `immament/football-match-viewer`, has no licence. Keep the in-house renderer from 06.

### Overlay and graphics starters

| Repo | Use | Licence · stars · last push |
|---|---|---|
| [ebu/ograf](https://github.com/ebu/ograf) `v1/examples` | `l3rd-name`, `responsive-lower-third`, `scoreboard`, `bar-chart`, `headline`, `minimal`: copy as our cue-template base | MIT · 139 · 2026-10-04 |
| [SuperFlyTV/ograf-server](https://github.com/SuperFlyTV/ograf-server) | Ready OGraf renderer page (load into OBS/CasparCG) + upload/control API + controller page; Node 20+ | MIT · 41 · 2026-10-15 |
| [SuperFlyTV/ograf-devtool](https://github.com/SuperFlyTV/ograf-devtool) · [nytamin/ograf-graphics](https://github.com/nytamin/ograf-graphics) | Template dev harness · more example graphics | MIT · 23 / 14 |
| [TuomoKu/SPX-GC](https://github.com/TuomoKu/SPX-GC) | Controller for HTML and OGraf templates; templates in `ASSETS/templates/softpix` | MIT · 427 · 2026-06-16 |
| [chrisryanouellette/CasparCG-Guide-HTML-Template](https://github.com/chrisryanouellette/CasparCG-Guide-HTML-Template) | Minimal CasparCG `play/stop/update` template | MIT · 12 · 2023 |
| [JacoboSanchez/volley-overlay-control](https://github.com/JacoboSanchez/volley-overlay-control) | **Closest stack analogue:** FastAPI + React 19/TS, 28 OBS browser-source overlays served in-process | Apache-2.0 · 6 · 2026-10-17 |
| Avoid: `zerodensity/ograf-studio` (AGPL-3.0), `k4kfh/casparcg-html-templates` (GPL-3.0, archived), `casparcg-vue-boilerplate` (no licence) | | |

### Video/CV and capture

- **CV code:** [roboflow/sports](https://github.com/roboflow/sports) (MIT, 5.4k, 2026-08-28; `examples/soccer`) and [roboflow/notebooks](https://github.com/roboflow/notebooks) `football-ai.ipynb` / `how-to-track-football-players.ipynb` (9.7k stars, **no licence file**). Read them; don't copy wholesale. The AGPL weights risk is in 05. Build on `supervision` (MIT, 51k), `rf-detr` (Apache-2.0, 9.8k) and `trackers` (Apache-2.0, 4.0k).
- **Capture:** Playwright Python (Apache-2.0, 15k) records with `browser.new_context(record_video_dir="videos/", record_video_size={...})`. The video is only written when the context closes. The docs mention no frame-rate control, so use 06's lockstep screenshot method for frame-exact renders.

### Codespaces / devcontainer

The Microsoft templates all ship `.devcontainer/` built on `mcr.microsoft.com/devcontainers/python` plus the `ghcr.io/azure/azure-dev/azd` feature. The Python image currently has 3.10–3.15 variants (trixie/bookworm). Official features we need are `node`, `azure-cli` and `docker-in-docker` (for the Event Hubs emulator). Free Codespaces: GitHub Free personal accounts get 15 GB-month storage and "120 hrs" of compute per month. GitHub Pro gets 20 GB-month and 180 hrs.

## So what for us

- **All stages, all ideas.** Don't fork a whole template. Start an empty repo with our own `azure.yaml` (two services, `worker` → `containerapp` and `web` → `staticwebapp`). Paste in Bicep for Event Hubs, Web PubSub, Cosmos DB, ACA jobs and SWA from AVM. Lift the ACA + MI + OpenAI role-assignment Bicep from `openai-chat-app-quickstart`. That gives one `azd up`, keyless.
- **Render stage (TwinCast, Graphics Desk, Speed Trap).** Make our cue templates OGraf graphics derived from `ebu/ograf/v1/examples/l3rd-name` and `scoreboard`. Use `ograf-server` as the local renderer in OBS. The same HTML runs in SPX or CasparCG. Our cue JSON maps onto OGraf `updateAction`.
- **Personalise stage.** The worker's `/negotiate` mints a Web PubSub token with `groups=[audience, club]`. SWA hosts only static files. Choose the SWA Free plan unless we want the `/api` proxy (Standard).
- **Interpret stage.** In `/sim`, use `floodlight` (speeds/distances), `socceraction` (xT/VAEP) and `mplsoccer` (report figures) as dev dependencies. Don't use `unravelsports` unless we accept MPL-2.0 on modified files.
- **Optional MCP endpoint.** Several rivals have one. Mount the official SDK's `MCPServer.streamable_http_app()` under `/mcp` on the same FastAPI worker. It exposes read-only tools such as `get_cues(match_id, since)` and `explain_moment(cue_id)`. That's about 30 lines, and needs no extra resource.

### Proposed repo skeleton

```
twincast/
├── azure.yaml                  # ours; hooks pattern from todo-python-mongo-swa-func (archived) + azure-search-openai-demo
├── docker-compose.yml          # Event Hubs emulator + Azurite (from 01)
├── .devcontainer/devcontainer.json   # from openai-chat-app-quickstart + node + docker-in-docker
├── .github/workflows/azure-dev.yml   # azd pipeline config output (azd pipeline config)
├── infra/
│   ├── main.bicep              # subscription scope, RG, UAMI, role assignments
│   ├── main.parameters.json    # AZURE_ENV_NAME / AZURE_LOCATION / AZURE_PRINCIPAL_ID
│   ├── abbreviations.json      # from any azd template
│   └── modules/                # thin wrappers over br/public:avm/res/... (event-hub/namespace 0.15.x,
│                               #   signal-r-service/web-pub-sub 0.7.x, app/container-app 0.23.x,
│                               #   app/job 0.7.x, web/static-site 0.9.x, document-db/database-account 0.21.x,
│                               #   cognitive-services/account 0.19.x)
├── sim/                        # Python pkg: seeded generator (02), Event Hubs publisher, ground truth
│   ├── twinsim/  generator.py  publisher.py  physics.py
│   └── render/                 # Three.js scene (TS) + Playwright capture (06) → ACA job image
├── worker/                     # Python FastAPI on ACA (minReplicas 1)
│   ├── Dockerfile              # from pamelafox/simple-fastapi-container
│   └── app/ main.py  consumer.py  stats/  explain.py (03)  cues.py  pubsub.py  mcp.py
│       cv/                     # RF-DETR + trackers grader (05) → separate ACA job image
├── web/                        # Vite + React + TS
│   ├── src/  pitch/ (d3-soccer)  console/ (Graphics Desk)  fan/ (personalised view)
│   └── public/ograf/           # cue graphics from ebu/ograf examples
├── data/  schemas/cue.schema.json  seeds/  sample-matches/  ground-truth/
└── docs/  architecture.md  demo-script.md  licences.md
```

## Reuse: code & links

**`azure.yaml`.** The `staticwebapp` + `prepackage` hook pattern comes from the archived todo template. `remoteBuild` comes from azure-search-openai-demo.

```yaml
name: twincast
services:
  worker:
    project: ./worker
    language: py
    host: containerapp
    docker: { path: ./Dockerfile, remoteBuild: true }
  web:
    project: ./web
    language: ts
    host: staticwebapp
    dist: dist
    hooks:
      prepackage:
        posix: { shell: sh, run: 'echo VITE_WORKER_URL=\"$WORKER_URL\" > .env.local' }
        windows: { shell: pwsh, run: 'echo "VITE_WORKER_URL=""$env:WORKER_URL""" > .env.local' }
```

**Keyless Web PubSub (AVM).** `disableLocalAuth` appears in the module README.

```bicep
module wps 'br/public:avm/res/signal-r-service/web-pub-sub:0.7.1' = {
  name: 'wps'
  params: { name: 'wps-${resourceToken}', location: location, sku: 'Free_F1', disableLocalAuth: true }
}
// then grant the worker UAMI the "Web PubSub Service Owner" role on it (role name unverified)
```

**Worker: negotiate + MCP on one FastAPI app.** The SDK signatures were checked. Wiring the MCP lifespan into FastAPI is unverified; the SDK docs show it with Starlette.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from azure.identity.aio import DefaultAzureCredential
from azure.messaging.webpubsubservice.aio import WebPubSubServiceClient
from mcp.server import MCPServer

mcp = MCPServer("twincast")

@mcp.tool()
def get_cues(match_id: str, since_ms: int = 0) -> list[dict]:
    """Return verified overlay cues for a match since a match-clock time."""
    return CUE_STORE.since(match_id, since_ms)

@asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield

app = FastAPI(lifespan=lifespan)
wps = WebPubSubServiceClient(endpoint=WPS_ENDPOINT, hub="match", credential=DefaultAzureCredential())

@app.get("/negotiate")
async def negotiate(user: str, audience: str = "casual", club: str = "neutral"):
    tok = await wps.get_client_access_token(user_id=user, groups=[f"aud.{audience}", f"club.{club}"])
    return {"url": tok["url"]}

app.mount("/mcp", mcp.streamable_http_app())
```

**Devcontainer.**

```json
{
  "image": "mcr.microsoft.com/devcontainers/python:3.12-bookworm",
  "features": {
    "ghcr.io/azure/azure-dev/azd:latest": {},
    "ghcr.io/devcontainers/features/node:1": {},
    "ghcr.io/devcontainers/features/azure-cli:1": {},
    "ghcr.io/devcontainers/features/docker-in-docker:2": {}
  },
  "postCreateCommand": "pip install uv && (cd worker && uv sync) && (cd web && npm ci)"
}
```

**Day-0 bootstrap.** The azd flags were checked against the azd reference.

```bash
# 0. harvest reference infra (throwaway dirs, not our repo)
azd init -t openai-chat-app-quickstart -e ref1     # creates ./openai-chat-app-quickstart
azd init -t pamelafox/simple-fastapi-container -e ref2
# 1. our repo
uv init --package sim && uv init --app worker
cd worker && uv add fastapi "uvicorn[standard]" azure-identity azure-eventhub azure-messaging-webpubsubservice openai "mcp[cli]" azure-cosmos && cd ..
npm create vite@latest web -- --template react-ts && (cd web && npm i @azure/web-pubsub-client d3-soccer)
(cd sim && uv add --dev mplsoccer floodlight socceraction kloppy)
# 2. local loop
docker compose up -d                                # Event Hubs emulator (01)
# 3. Azure
azd auth login
azd env new dev && azd env set AZURE_LOCATION <region-with-your-Foundry-model>
azd up                                              # provision + deploy worker and web
azd deploy worker                                   # fast inner loop afterwards
azd pipeline config                                 # GitHub Actions + federated creds (unverified on Students subs)
azd down --purge                                    # after judging
```

## Sources

- Awesome azd gallery — https://azure.github.io/awesome-azd/ (data: https://github.com/Azure/awesome-azd/blob/main/website/static/templates.json) — accessed 20 Oct 2026
- azure.yaml schema v1.0 — https://github.com/Azure/azure-dev/blob/main/schemas/v1.0/azure.yaml.json — accessed 20 Oct 2026
- azd releases — https://github.com/Azure/azure-dev/releases — accessed 20 Oct 2026
- azd CLI reference (init, env set, deploy, down) — https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/reference — accessed 20 Oct 2026
- Edit azd template files (hello-azd, AVM advice) — https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/explore-edit-templates — accessed 20 Oct 2026
- SWA API support with Functions — https://learn.microsoft.com/en-us/azure/static-web-apps/apis-functions — accessed 20 Oct 2026
- SWA API overview and constraints — https://learn.microsoft.com/en-us/azure/static-web-apps/apis-overview — accessed 20 Oct 2026
- openai-chat-app-quickstart — https://github.com/Azure-Samples/openai-chat-app-quickstart — accessed 20 Oct 2026
- rag-postgres-openai-python — https://github.com/Azure-Samples/rag-postgres-openai-python — accessed 20 Oct 2026
- get-started-with-ai-agents — https://github.com/Azure-Samples/get-started-with-ai-agents — accessed 20 Oct 2026
- get-started-with-ai-chat — https://github.com/Azure-Samples/get-started-with-ai-chat — accessed 20 Oct 2026
- azure-search-openai-demo azure.yaml — https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/azure.yaml — accessed 20 Oct 2026
- simple-fastapi-container — https://github.com/pamelafox/simple-fastapi-container — accessed 20 Oct 2026
- todo-python-mongo-swa-func (archived) — https://github.com/Azure-Samples/todo-python-mongo-swa-func — accessed 20 Oct 2026
- functions-quickstart-python-azd-eventhub — https://github.com/Azure-Samples/functions-quickstart-python-azd-eventhub — accessed 20 Oct 2026
- Azure Verified Modules (bicep-registry-modules) — https://github.com/Azure/bicep-registry-modules/tree/main/avm/res — accessed 20 Oct 2026
- Azure Web PubSub samples — https://github.com/Azure/azure-webpubsub/tree/main/samples — accessed 20 Oct 2026
- Web PubSub Python SDK `get_client_access_token` — https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/webpubsub/azure-messaging-webpubsubservice/azure/messaging/webpubsubservice/aio/_operations/_patch.py — accessed 20 Oct 2026
- Microsoft Agent Framework Python samples — https://github.com/microsoft/agent-framework/tree/main/python/samples — accessed 20 Oct 2026
- MCP Python SDK README and docs_src (asgi, deploy) — https://github.com/modelcontextprotocol/python-sdk — accessed 20 Oct 2026
- python-mcp-demos — https://github.com/Azure-Samples/python-mcp-demos — accessed 20 Oct 2026
- remote-mcp-functions-python — https://github.com/Azure-Samples/remote-mcp-functions-python — accessed 20 Oct 2026
- mplsoccer / kloppy / socceraction / floodlight / databallpy / unravelsports / penaltyblog — GitHub repo pages as linked in tables — accessed 20 Oct 2026
- d3-soccer — https://github.com/probberechts/d3-soccer — accessed 20 Oct 2026
- Soccermatics — https://github.com/soccermatics/Soccermatics and https://soccermatics.readthedocs.io — accessed 20 Oct 2026
- EBU OGraf examples — https://github.com/ebu/ograf/tree/main/v1/examples — accessed 20 Oct 2026
- SuperFlyTV ograf-server — https://github.com/SuperFlyTV/ograf-server — accessed 20 Oct 2026
- SPX-GC — https://github.com/TuomoKu/SPX-GC — accessed 20 Oct 2026
- volley-overlay-control — https://github.com/JacoboSanchez/volley-overlay-control — accessed 20 Oct 2026
- roboflow/sports and roboflow/notebooks — https://github.com/roboflow/sports , https://github.com/roboflow/notebooks — accessed 20 Oct 2026
- Playwright Python videos — https://playwright.dev/python/docs/videos — accessed 20 Oct 2026
- Dev Container features and images — https://github.com/devcontainers/features , https://github.com/devcontainers/images — accessed 20 Oct 2026
- GitHub Codespaces billing (included usage) — https://docs.github.com/en/billing/concepts/product-billing/github-codespaces — accessed 20 Oct 2026
