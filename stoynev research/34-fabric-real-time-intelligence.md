# 34 — Microsoft Fabric Real-Time Intelligence: is it worth adding?

_Accessed/compiled: 20 Oct 2026 · Priority area: Interpret stage (side analytics), Technological Implementation and "Enterprise" scoring, analyst persona for F Graphics Desk / A TwinCast / B Speed Trap_

## TL;DR

- **Verdict: an optional side quest, capped at about half a day, and only after the TwinCast core loop works.** Point a Fabric Eventstream at our existing Event Hub through its own consumer group. Land the events in an Eventhouse (KQL), build a 4-tile Real-Time Dashboard, add one Activator rule ("speed > 34 km/h → Teams/email"), and show it in the video and README. The hot path doesn't change. It earns a Fabric "hero technology" tick, but it is not a differentiator: 16 of 332 projects already mention Fabric.
- **Judges can't open it.** Real-Time Dashboards live inside a Fabric tenant. Viewers need dashboard permission and either their own data access or an editor's cloud connection, so this can never be the public demo link. It only works as video footage and screenshots.
- **The trial is free for 60 days (F4 or F64), but it excludes data agents and Copilot.** It also needs a work or school account, because Gmail and Hotmail sign-ups are refused. A data agent needs a **paid F2+**. At the East US list price that is **$0.18 per CU-hour, so F2 costs $0.36/h** (about $8.64/day if left running). You can pause it and billing stops.
- **Watch for the Foundry retirement trap.** The old Foundry "Microsoft Fabric" tool (`FabricTool`) **stops being supported on 6 Nov 2026**, which falls in the middle of judging (27 Oct to 10 Nov). If we do the agent angle, we must use the new **Fabric IQ (OneLake Catalog)** tool or the data agent's **MCP endpoint**. Both are preview.
- **The KQL itself is a real asset.** `make-series` plus `series_fir` gives a rolling possession share, and `countif` by 10-minute bins gives PPDA. Ready-to-paste queries are below. We can reuse them as the "recompute the claim" step of our fact-checker, whether or not we keep Fabric.

## Findings

### 1. What each component does (and what we would use)

| Component | What it is | Use for us |
|---|---|---|
| **Eventstream** | No-code ingest, transform and route. Its sources include Azure Event Hubs, Kafka, CDC and a **custom endpoint** that exposes an Event Hub-compatible, AMQP or Kafka connection string. It can filter, aggregate over windows and route by content. | Side-tap the Event Hub. Fan out to Eventhouse and Activator. |
| **Eventhouse / KQL DB** | A time-series analytics store. You query it in KQL (or T-SQL), and it has native anomaly detection. Data can be mirrored to OneLake. | Store events, compute stats. |
| **Real-Time Dashboard** | KQL-backed tiles with parameters, pages, Copilot tile authoring and **Live refresh**. Live refresh is on by default for new dashboards. Each visual runs a lightweight `ingestion_time()` "high-water mark" check and re-queries only when new data lands. A "refresh rate limit" setting caps how often it refreshes. | The analyst screen. |
| **Activator** | A no-code rules engine over eventstreams, dashboards, KQL and Power BI. It groups events into **objects** by an ID column (for us, `player_id`). Rules can be stateless or stateful (`BECOMES`, `INCREASES`, `EXIT RANGE`, heartbeat) and fire only on entry into a new state. Actions include email, Teams, Power Automate, pipelines, notebooks and User Data Functions. Microsoft quotes "subsecond for stateless rules on streaming data". | The speed alert. |
| **Fabric data agent** | A GA conversational Q&A agent that runs NL2KQL, NL2SQL and NL2DAX over up to 5 sources, Eventhouse included. It is read-only, English-only, and caps answers at 25 rows × 25 columns. | The analyst asks "who pressed hardest after 60'?" |
| **Fabric IQ tool / data agent MCP** | Every published data agent is an MCP server at `https://api.fabric.microsoft.com/v1/mcp/workspaces/{ws}/dataagents/{id}/agent`. Foundry adds it through the Fabric IQ tool, which allows several data agents per Foundry agent. | Foundry orchestrator → data agent. |
| **Fabric MCP servers** | `microsoft/fabric-rti-mcp` (MIT, public preview): `kusto_query`, Eventstream builder and `activator_create_trigger` tools. Separately, `microsoft/mcp` Fabric server has 19 OneLake commands. | Copilot Agent Mode dev tooling. A possible verifier-agent tool. |

### 2. Simplest side-consumer tap (hot path unchanged)

1. In the Azure portal, create a **new consumer group `fabric`** on our hub. Event Hubs Standard gives 20 consumer groups but **Basic gives only 1**, so on Basic, Fabric would compete with our worker for `$Default` (research 01).
2. Create a SAS policy with *Listen* rights, or grant the Fabric **workspace identity** the *Azure Event Hubs Data Receiver* role (extended features). The hub must be public, not behind a firewall, unless we set up a managed private endpoint.
3. In Fabric, go to **New item → Eventstream → Connect data sources → Azure Event Hubs**. Enter the namespace, hub name, key, consumer group `fabric` and data format **JSON**, then **Publish**.
4. **Add destination → Eventhouse → Direct ingestion.** In Live view, select **Configure**, then **New table `MatchEvents`** and **Finish**.
5. (Optional) **Add destination → Activator.**

An alternative with fewer items is to skip Eventstream and use **Eventhouse → Get data → Event Hubs** directly. It supports SAS only, and Activator would then have to watch a dashboard or KQL query instead of the stream.

**Latency caveat.** Kusto's queued (batched) ingestion defaults to a **5-minute** maximum batching delay. The "low latency" setting is 20 to 30 s, and the minimum is 10 s. Streaming ingestion targets "less than a second", but its policy page is marked as applying to Azure Data Explorer only, so how Fabric's Eventstream direct ingestion handles this is **unverified**. Measure it with the `lag_s` tile below before relying on it.

### 3. Cost and trial for a student or personal account

| Option | Cost | Gotchas |
|---|---|---|
| **Fabric trial capacity** | Free for **60 days**. It is **F4 or F64** (an admin can switch it from 4 to 64 CU if eligible), with 1 TB of OneLake. | **No Copilot, no data agent, no AI functions.** It needs a Fabric (Free) per-user license, which means a **work or school email**. Docs: "You can't use consumer email accounts (for example, Gmail or Hotmail)". The documented workaround is a Microsoft 365 trial tenant (`onmicrosoft.com`), which needs a credit card and lasts 30 days. Creating a user in the Entra directory of our existing Azure subscription may also work (**unverified**). Trial items go inactive at expiry and are kept for 7 days. |
| **F2 pay-as-you-go** | **$0.18/CU-hour** in East US (Azure Retail Prices API, meter "Fabric Capacity Usage CU"). So F2 is **$0.36/h**, about **$8.64/day** or **$262.80 per 730-hour month** (our arithmetic). Billing is per second with a 1-minute minimum. | It can be **paused** in the portal, by REST or by runbook, and pausing stops billing. Any remaining smoothed and overage usage is billed at pause time. 10 hours of dev and recording would cost about $3.60. Whether F2 runs Eventstream, Eventhouse and the dashboard without throttling is **unverified**. The public pricing page renders prices client-side, so we couldn't read F2 from the page itself. |

Other notes:
- Below F64, people viewing **Power BI** items need Pro or PPU. That doesn't affect Real-Time Dashboards, which are non-Power BI items.
- Put the capacity in the **same region** as the Event Hub, which Microsoft recommends for latency and egress.
- The data agent also fails if the agent's capacity and the source's capacity are in different regions.

### 4. Does the dashboard plus alert add judging value?

- **Technological Implementation** names Fabric among the hero technologies (research 12), so using it costs nothing against the rubric and gets us a mention.
- **UX & Presentation** sees almost no gain. Judges can't click the dashboard, and our own viewer is the product. Five seconds of an "analyst desk" in the video is the most it is worth.
- **Agentic / Enterprise** is the stronger angle (section 5), but it needs paid F2 and preview integrations during judging.
- **Effort:** about 2 to 3 h for the tap, table and 4 tiles, about 1 h for Activator, and 2 to 4 h for the data agent and Foundry. Add the account and tenant friction on top.
- **Verdict:** do the **dashboard plus Activator on trial** only if a work/school tenant is already at hand. Otherwise **skip Fabric** and put that time into TwinCast grading. Activator alerts go to producers (Teams). They are not the cue engine: on-screen cues stay in our own worker, whose latency we control.

### 5. Data agent + Foundry as an "Agentic / Enterprise" story

The pitch: *"Our Foundry studio crew has a governed analyst tool. The Analyst agent asks the Fabric data agent over MCP, and Fabric runs NL2KQL under the user's own identity (on-behalf-of), read-only, with Purview-governed access."*

Wiring options:
- **Portal:** Agent → **Tools → Add → Fabric IQ (OneLake Catalog)** → filter Type = Data agent → Add. This needs the **Foundry Project Manager** role to create the connection and **Foundry User** to build. Fabric and Foundry must be in the **same tenant**, signed in with the same account.
- **Code:** any MCP client works. Our Agent Framework code can call the data agent's MCP endpoint with a bearer token for `https://api.fabric.microsoft.com/.default`. The docs say this can be a user or a **service principal**.

Limits that matter for us:
- English only, so we translate after it answers.
- 25 rows maximum, and up to 100 example queries per source.
- No writes.
- Responses "may be sent outside Fabric's compliance boundary". That doesn't matter with synthetic data, but it's worth stating in the Responsible AI notes.

**Risk:** every path is preview, and the legacy `FabricTool` sample on Learn stops being supported on 6 Nov 2026, so **don't copy it**.

### 6. What competitors use Fabric for

- **OmniPitch (126721):** claims "Fabric Lakehouse Integration" with Delta tables (`fact_match_events`, `dim_player_physical_summary`). In the public repo, `src/omnipitch/analytics/fabric_export.py` only flattens events into dicts and imports nothing but `json`/`typing`. **We found no code that writes to OneLake.** It is Fabric as a label.
- **LiveDesk (126529):** "Fabric agent". **Pitch Ledger (126391):** "Audited claims; Fabric IQ". **MatchDirector (126336):** "Fabric IQ". These come from one-line intel notes; we haven't seen the details (**unverified**).
- So the field uses Fabric mostly as a **data agent or IQ badge**. Nobody we have seen shows live KQL metrics or Activator.

## So what for us

- **Stages:** Interpret (side analytics), plus Personalise (the analyst persona).
- **Ideas it helps:**
  - **F Graphics Desk**: the producer gets Teams alerts and an analyst wall.
  - **B Speed Trap**: an Activator speed rule.
  - **C One Number**: PPDA and possession tiles.
  - **A TwinCast**: the grader's KQL lives next to the ground truth.
- **Recommendation:**
  1. Ship nothing in Fabric before the core loop works.
  2. Then, if a work/school tenant exists, start the free trial in our Event Hub region. Add a `fabric` consumer group, Eventstream → Eventhouse `MatchEvents` + `PlayerSpeed`, the 4 tiles below and one Activator rule. Record it for the video and screenshot it into the README.
  3. Only pay for F2 (pause it when idle) if we also want the data agent / Fabric IQ angle. Wire it through the **MCP endpoint**, not `FabricTool`.
  4. Whatever we decide, **reuse the KQL logic** as the fact-checker's deterministic "recompute" step. It is identical whether the data sits in Eventhouse or is replayed by our Python worker.

## Reuse: code & links

Assumed columns: `MatchEvents(match_id, event_id, type, team_id, player_id, time_s:real, x:real, attack_dir:int, t_emit:real)`. Here `x` is metres from the centre spot (CDF, research 02) and `attack_dir` is +1 or -1 for the acting team in that period, so `x_att = 52.5 + x*attack_dir` means 0 at the team's own goal and 105 at the opponent's goal. The second table is `PlayerSpeed(match_id, t_s:real, player_id, team_id, speed_kmh:real)` at about 1 Hz from our tracker. Change the `type` names to whatever our generator emits.

```kusto
// 0. Latency check (pipeline lag, seconds). Do this first.
MatchEvents
| where ingestion_time() > ago(10m)
| extend lag_s = datetime_diff('millisecond', ingestion_time(), unixtime_seconds_todatetime(t_emit)) / 1000.0
| summarize p50 = percentile(lag_s, 50), p95 = percentile(lag_s, 95) by bin(ingestion_time(), 1m)
| render timechart
```

```kusto
// 1. Rolling possession share (5-minute trailing window on pass counts)
let m = "syn-0001";
MatchEvents
| where match_id == m and type == "pass"
| extend match_min = toint(time_s / 60)
| make-series home = countif(team_id == "home"), away = countif(team_id == "away") default = 0
    on match_min from 0 to 96 step 1
| extend home5 = series_fir(home, dynamic([1,1,1,1,1]), false, false),
         away5 = series_fir(away, dynamic([1,1,1,1,1]), false, false)
| mv-expand match_min to typeof(int), home5 to typeof(real), away5 to typeof(real)
| extend home_pct = iff(home5 + away5 == 0, real(null), round(100.0 * home5 / (home5 + away5), 1))
| project match_min, home_pct, away_pct = 100 - home_pct
| render timechart
```

```kusto
// 2. PPDA per 10 minutes (Trainor-style: defensive actions in the opponent's 60%,
//    opponent passes in their own 60%; see research 09). Lower PPDA = more intense press.
let m = "syn-0001";
let def_types = dynamic(["tackle", "interception", "challenge", "foul"]);
MatchEvents
| where match_id == m
| extend x_att = 52.5 + x * attack_dir, seg = toint(time_s / 600) * 10
| summarize
    def_home  = countif(team_id == "home" and type in (def_types) and x_att > 42),
    def_away  = countif(team_id == "away" and type in (def_types) and x_att > 42),
    pass_home = countif(team_id == "home" and type == "pass" and x_att < 63),
    pass_away = countif(team_id == "away" and type == "pass" and x_att < 63)
  by seg
| extend ppda_home = iff(def_home == 0, real(null), round(1.0 * pass_away / def_home, 1)),
         ppda_away = iff(def_away == 0, real(null), round(1.0 * pass_home / def_away, 1))
| project window = strcat(seg, "-", seg + 10, "'"), ppda_home, ppda_away
| order by window asc
```

```kusto
// 3. Top speeds (from PlayerSpeed); if only raw positions exist, smooth first
//    over 5 frames: speed = distance(prev(x,5), x) / (t - prev(t,5)) * 3.6
let m = "syn-0001";
PlayerSpeed
| where match_id == m
| summarize top_kmh = round(max(speed_kmh), 1), at_s = arg_max(speed_kmh, t_s) by player_id, team_id
| project player_id, team_id, top_kmh, at_min = round(at_s / 60, 1)
| top 10 by top_kmh
```

```kusto
// 4. Events per minute, stacked by type (rhythm tile)
let m = "syn-0001";
MatchEvents
| where match_id == m
| summarize events = count() by match_min = toint(time_s / 60), type
| render columnchart with (kind = stacked)
```

~~~kusto
// Optional: reduce queued-ingestion delay if streaming isn't in effect (minimum 10 s)
.alter table MatchEvents policy ingestionbatching
```
{ "MaximumBatchingTimeSpan": "00:00:10", "MaximumNumberOfItems": 500, "MaximumRawDataSizeMB": 1024 }
```
~~~

**Activator, minimal steps:**
1. In Eventstream edit mode, choose **Add destination → Activator**, create a new Activator item and publish.
2. In Activator, create a **new object** from the stream with **Object ID = `player_id`** and property `speed_kmh`.
3. Create a **new rule**: numeric condition `speed_kmh` greater than 34. Because it is stateful, it fires only on the crossing.
4. Set the action to **Teams message** (or email) with `player_id`, `speed_kmh` and `t_s` in the template.
5. Use the preview, which estimates how often the rule would have fired on history, and then **Start**.

**Data agent over MCP (Python, from Learn; works from our worker or Agent Framework):**

```python
import asyncio
from azure.identity import DefaultAzureCredential
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "https://api.fabric.microsoft.com/v1/mcp/workspaces/<ws-id>/dataagents/<agent-id>/agent"
cred = DefaultAzureCredential()

async def ask(q: str) -> str:
    tok = cred.get_token("https://api.fabric.microsoft.com/.default").token
    async with streamablehttp_client(URL, headers={"Authorization": f"Bearer {tok}"}) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tool = (await s.list_tools()).tools[0]            # the agent exposes one tool
            arg = next(iter(tool.inputSchema["properties"]))
            res = await s.call_tool(tool.name, {arg: q})
            return "\n".join(b.text for b in res.content if b.type == "text")

print(asyncio.run(ask("Which team had the lower PPDA between minute 60 and 90 in match syn-0001?")))
```

**Dev tooling:** `uvx microsoft-fabric-rti-mcp` in VS Code gives Copilot Agent Mode `kusto_query` and `activator_create_trigger` tools. This is useful for drafting the tiles, and it's another hero-tech mention: https://github.com/microsoft/fabric-rti-mcp

## Sources

- What Is Real-Time Intelligence in Microsoft Fabric? — https://learn.microsoft.com/en-us/fabric/real-time-intelligence/overview — accessed 20 Oct 2026
- Add an Azure Event Hubs source to an eventstream — https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/add-source-azure-event-hubs — accessed 20 Oct 2026
- Add a custom endpoint or custom app source to an eventstream — https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/add-source-custom-app — accessed 20 Oct 2026
- Add an Eventhouse destination to an eventstream — https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/add-destination-kql-database — accessed 20 Oct 2026
- Get data from Azure Event Hubs (Eventhouse) — https://learn.microsoft.com/en-us/fabric/real-time-intelligence/get-data-event-hub — accessed 20 Oct 2026
- IngestionBatching policy (Fabric) — https://learn.microsoft.com/en-us/kusto/management/batching-policy?view=microsoft-fabric — accessed 20 Oct 2026
- Streaming ingestion policy — https://learn.microsoft.com/en-us/kusto/management/streaming-ingestion-policy — accessed 20 Oct 2026
- Configure streaming ingestion (ADX) — https://learn.microsoft.com/en-us/azure/data-explorer/ingest-data-streaming — accessed 20 Oct 2026
- series_fir() — https://learn.microsoft.com/en-us/kusto/query/series-fir-function?view=microsoft-fabric — accessed 20 Oct 2026
- Create a Real-Time Dashboard — https://learn.microsoft.com/en-us/fabric/real-time-intelligence/dashboard-real-time-create — accessed 20 Oct 2026
- Live refresh in Real-Time Dashboard — https://learn.microsoft.com/en-us/fabric/real-time-intelligence/dashboard-live-refresh — accessed 20 Oct 2026
- Real-Time Dashboard permissions — https://learn.microsoft.com/en-us/fabric/real-time-intelligence/dashboard-permissions — accessed 20 Oct 2026
- What is Fabric Activator? — https://learn.microsoft.com/en-us/fabric/real-time-intelligence/data-activator/activator-introduction — accessed 20 Oct 2026
- Fabric trial capacity — https://learn.microsoft.com/en-us/fabric/fundamentals/fabric-trial — accessed 20 Oct 2026
- Microsoft Fabric licenses and capacity (SKU/CU table) — https://learn.microsoft.com/en-us/fabric/enterprise/licenses — accessed 20 Oct 2026
- Pause and resume your Fabric capacity — https://learn.microsoft.com/en-us/fabric/enterprise/pause-resume — accessed 20 Oct 2026
- Sign up or purchase Power BI as an individual (work/school email rule) — https://learn.microsoft.com/en-us/power-bi/fundamentals/service-self-service-signup-purchase-for-power-bi — accessed 20 Oct 2026
- Microsoft Fabric pricing page (prices render client-side; not readable) — https://azure.microsoft.com/en-us/pricing/details/microsoft-fabric/ — accessed 20 Oct 2026
- Azure Retail Prices API, serviceName 'Microsoft Fabric', eastus — https://prices.azure.com/api/retail/prices?$filter=serviceName%20eq%20'Microsoft%20Fabric'%20and%20armRegionName%20eq%20'eastus' — accessed 20 Oct 2026
- Fabric data agent concepts — https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent — accessed 20 Oct 2026
- Consume a data agent in Microsoft Foundry (retiring 6 Nov 2026) — https://learn.microsoft.com/en-us/fabric/data-science/data-agent-foundry — accessed 20 Oct 2026
- Consume Fabric data agent from Foundry via Fabric IQ (preview) — https://learn.microsoft.com/en-us/fabric/data-science/data-agent-foundry-fabric-iq — accessed 20 Oct 2026
- Data agent as Model Context Protocol server — https://learn.microsoft.com/en-us/fabric/data-science/data-agent-mcp-server — accessed 20 Oct 2026
- Use AI agents with OneLake through MCP — https://learn.microsoft.com/en-us/fabric/onelake/onelake-local-mcp — accessed 20 Oct 2026
- microsoft/fabric-rti-mcp (README, MIT, public preview) — https://github.com/microsoft/fabric-rti-mcp — accessed 20 Oct 2026
- riccardoponte/OmniPitch (README and fabric_export.py) — https://github.com/riccardoponte/OmniPitch — accessed 20 Oct 2026
- Internal: Berbata_Hackathon_Intel.md (Fabric mention count; LiveDesk, Pitch Ledger, MatchDirector notes); research 01, 09, 12, 16, 21 — accessed 20 Oct 2026
