# 01 — Azure services for each pipeline stage (real-time path)

_Accessed/compiled: 20 Oct 2026 · Priority area: architecture / real-time plumbing (Ingest → Render)_

## TL;DR

- **Minimal stack:** Event Hubs **Standard** (1 TU) → one always-on **Python worker on Azure Container Apps** (does the windowed stats itself, calls the Foundry model) → **Azure Web PubSub** groups (one group per audience profile) → **Static Web Apps** front end. State in **Cosmos DB free tier** (provisioned, not serverless). Skip Stream Analytics and Redis for v1.
- **Develop offline first:** there is an official **Event Hubs emulator** (Docker + Azurite, AMQP and Kafka). Same `azure-eventhub` code, different connection string.
- **Use Standard, not Basic:** Basic allows only 1 consumer group, no Kafka, no Capture and 256 KB events. Standard gives 20 consumer groups, Kafka, 7-day retention and Capture (paid add-on).
- **Web PubSub Free_F1 is for dev only:** 20 concurrent connections and 20,000 outbound messages per day. Move to Standard (1 unit = 1,000 connections, 1M messages/day included) before demo day.
- **Latency enemy #1 is scale-from-zero, not the services.** KEDA polls every 30 s and Stream Analytics windows only emit at window end. Keep the hot path warm (`minReplicas: 1`) and do the windowing in our own code.

## Findings

### 1. Stage-by-stage map

| Stage | Primary pick | Alternatives (1-2) | Why |
|---|---|---|---|
| **Ingest** (synthetic events) | Event Hubs Standard, partition key = `match_id` | Event Hubs emulator (local); Kafka clients pointed at the Event Hubs Kafka endpoint (port 9093) | Ordered per partition, replayable (retention), many readers via consumer groups |
| **Interpret** (stats, windows, patterns) | Python async consumer on **Container Apps** (min 1 replica) | Azure Stream Analytics job (1/3 SU V2); Functions Flex Consumption with Event Hubs trigger | Window maths in Python is easier to test, and we already need Python for the cue contract |
| **Explain** (why it matters) | **Microsoft Foundry** model / agent called from the worker | Self-hosted model on ACA **serverless GPU** (T4/A100); Foundry hosted agent | "Azure AI Foundry is now Microsoft Foundry"; AI Services are now "Foundry Tools" |
| **Render** (timed cue JSON to overlays) | **Web PubSub** `send_to_group` → browser `@azure/web-pubsub-client` | SignalR Service (if we wanted the SignalR protocol/.NET); a raw WebSocket from the ACA app | Generic WebSocket pub/sub, Python server SDK, groups map to audiences |
| **Personalise** (analyst/casual, club, language) | One Web PubSub group per profile + profile docs in **Cosmos DB** | Azure Managed Redis (hot state); in-memory dict in the single worker | Fan-out is cheapest when the worker renders each variant once per group |

### 2. Event Hubs (ingest)

**Tiers (from the quotas page):**

| Limit | Basic | Standard | Premium |
|---|---|---|---|
| Max event/batch size | 256 KB | 1 MB | 1 MB |
| Consumer groups per hub | **1** | 20 | 100 |
| Retention | 1 day | 7 days | 90 days |
| Partitions per hub | 32 | 32 | 100 (200 per PU at namespace) |
| Event hubs per namespace | 10 | 10 | 100 per PU |
| Brokered connections | 100 | 5,000 | 10,000 per PU |
| Kafka endpoint | No | Yes | Yes |
| Capture | N/A | Priced separately | Included |
| Throughput unit | 1 TU = ingress 1 MB/s or 1,000 events/s; egress 2 MB/s or 4,096 events/s | same | no per-PU limit |

- **Partitions:** one match per partition key keeps events in order. 2-4 partitions is plenty. The Stream Analytics docs note that 1/3 SU is usually enough for a 2-partition hub, which is a useful hint for sizing.
- **Kafka:** Standard tier and above. Use `bootstrap.servers=NAMESPACE.servicebus.windows.net:9093`, `SASL_SSL`, `PLAIN` with username `$ConnectionString`. Topic = event hub. Delivery is at-least-once, so consumers must be idempotent (dedupe on `event_id`).
- **Capture:** writes Avro to Blob/ADLS Gen2 on a time-or-size window ("first wins"). It is a cheap cold path for replays, not needed on the hot path. Not available in Basic or the emulator.
- **Throughput maths for us:** 1 TU allows 1,000 events/s ingress. Discrete events (passes, shots) are far below that. For **tracking frames** (TwinCast, Speed Trap) send **one event per frame holding all players**, not one per player.
- **Python SDK:** `azure-eventhub` (async in `azure.eventhub.aio`). If you don't pass a checkpoint store, checkpoints are kept in memory and there is no load-balancing. That is fine for one worker. `starting_position="@latest"` reads only new events and `"-1"` reads from the start, which is handy for replay. Blob checkpointing uses `azure-eventhub-checkpointstoreblob-aio`.
- **Emulator:** Docker image `mcr.microsoft.com/azure-messaging/eventhubs-emulator:latest`, plus Azurite. Ports 5672 (AMQP) and 9092 (Kafka). You configure entities in `config.json` before start-up. Connection string: `Endpoint=sb://localhost;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=SAS_KEY_VALUE;UseDevelopmentEmulator=true;`. Limits: 1 namespace, 10 hubs, 32 partitions, 20 consumer groups, 1 MB events. **Data does not persist across restarts.** It has no Capture, no Entra ID and no metrics. For Kafka, only the producer and consumer APIs work.

### 3. Stream Analytics vs windowing in Python

Stream Analytics (ASA) has five window types: **Tumbling** (fixed and non-overlapping), **Hopping** (fixed, overlapping, emits every hop), **Sliding** (emits only when an event enters or leaves the window), **Session** (groups bursts and closes after a timeout, with a max duration) and **Snapshot** (same timestamp). Example: `GROUP BY TimeZone, TumblingWindow(second,10)`.

The catches for us:
- **All windows output at the end of the window.** A 10 s tumbling window adds up to 10 s of delay by design.
- It runs constantly. The smallest job is 1/3 SU V2. There is no free tier (unverified: pricing not fetched).
- It is another language (SQL-like) and another deploy unit. Getting output to browsers still needs an extra hop. (Unverified: ASA has no direct Web PubSub output, so we'd go via Functions or Event Hubs.)

**Verdict:** do the windowing in Python (a deque per metric with a time-based expiry). We need custom football logic anyway (pressure, "control vs chaos", pass difficulty) that doesn't fit `GROUP BY`. ASA is worth it only if a judge-facing "uses Azure streaming analytics" box matters. If so, run it as a side consumer group and keep it off the hot path.

### 4. Azure Functions (Flex Consumption) vs Azure Container Apps

| | Functions Flex Consumption | Container Apps |
|---|---|---|
| Event Hubs integration | Native trigger (`@app.event_hub_message_trigger`), target-based scaling | KEDA `azure-eventhub` scaler (`unprocessedEventThreshold` default 64), or just run a long-lived consumer |
| Cold start control | "Always ready" instances (billed baseline; no free grant in that mode) | `minReplicas: 1` (idle replicas billed at a lower rate) |
| Limits | Linux only; Python 3.10–3.14; instance sizes 512 MB / 2 GB / 4 GB; one app per plan; host init times out after 30 s; max scale 1,000 | Default 0–10 replicas (up to 1,000); polling 30 s; cooldown 300 s |
| Quota gotcha | Free Trial and **Azure for Students** subscriptions get a **15-core** regional Flex quota (vs 250 standard) | GPU quota must be requested; pay-as-you-go/EA have T4/A100 enabled by default |
| Extras | Min billable execution is 1,000 ms | **Jobs** (event-driven or scheduled, good for batch render/CV); **serverless GPU** (T4, A100, scale to zero, per-second billing, Consumption workload-profile env only) |

**Pick ACA** for the hot path. A single long-lived async consumer keeps in-memory window state, which a stateless Function doesn't. It also shares a platform with TwinCast's GPU/CV jobs. Use Functions only for small HTTP glue such as the Web PubSub negotiate endpoint, ideally as an SWA managed API.

### 5. Pushing to browsers: Web PubSub vs SignalR Service

The Free and Standard limits are **identical** for the two services:

| | Free | Standard / Premium |
|---|---|---|
| Units per instance | 1 | up to 100 (Premium_P2: 100–1,000) |
| Concurrent connections per unit | **20** | 1,000 |
| Messages per unit per day | **20,000** included, no overage | 1,000,000 included, overage allowed |
| SLA | none | 99.9% Standard / 99.95% Premium |

- Billing counts **outbound** messages only. Messages over 2 KB count as multiple 2 KB messages. Example: 5 browser tabs at 1 cue/s is 18,000 messages/hour, which uses up the Free daily quota in about an hour of testing.
- Moving between the Free and Standard tiers changes the public IP, and DNS can take **30–60 minutes**. Scale up **days before** the demo.
- **Choosing between them:** Microsoft's FAQ says to pick SignalR if you already use ASP.NET SignalR or need RPC, streaming and long-polling fallbacks. Pick Web PubSub for plain WebSocket pub/sub and lightweight servers. We are Python + TS, so **Web PubSub**.
- **Python server SDK:** `azure-messaging-webpubsubservice`, with sync and `.aio` clients. It provides `send_to_group(group, message, content_type=...)`, `add_connection_to_group`, and `get_client_access_token(user_id=, roles=, groups=, minutes_to_expire=)`, which returns `{baseUrl, token, url}`. Group names can be 1–1,024 characters.
- **JS client:** `@azure/web-pubsub-client`. Call `client.on("group-message", ...)`, then `client.start()`, then `client.joinGroup(name)`. The docs still call the client SDK preview.
- **Groups per audience:** `m_{match}_casual_en`, `m_{match}_analyst_en`, `m_{match}_club_{SYN_CLUB}`, `m_{match}_metric_{name}` (One Number); we avoid `:` and `.` in names to be safe with role strings (unverified whether they are allowed). The server renders each cue once per group. Switching mode just means leave one group and join another, with no reconnect. Grant `webpubsub.joinLeaveGroup.<group>` roles in the token.
- **Performance note:** latency inside the service "remains low" while the Server Load metric is under 70%. A Unit 1 send-to-big-group benchmark reached 3,000 outbound messages/s, measured at p99 < 1 s.

### 6. State: Cosmos DB vs Redis

- **Cosmos DB free tier:** the first **1,000 RU/s and 25 GB** are free for the life of the account. You get one per subscription and must opt in at creation. **It is not available for serverless accounts.** A shared-throughput database can hold up to 25 containers. With the Azure free account, the first 12 months total 1,400 RU/s and 50 GB.
- **Serverless:** pay per RU consumed, single region only. The SLO is < 10 ms point reads and < 30 ms writes. Provisioned throughput has an SLA of < 10 ms for both reads and writes.
- **Redis:** *Azure Cache for Redis* Basic/Standard/Premium retire on **30 Sep 2028** and Enterprise on **31 Mar 2027**. Microsoft says to use **Azure Managed Redis** instead, which is Redis 7.4 and clustered by default. The smallest SKU is Balanced 0.5 GB. No free tier was found.
- **Verdict:** use Cosmos DB free tier (provisioned) for viewer profiles, the cue log (`cue_id`, evidence ids, truth_check) and match snapshots. Keep live window state in the worker's memory. Add Managed Redis only if we run more than one worker replica.

### 7. Static Web Apps (front end)

- **Free plan:** 100 GB/month bandwidth (no overage), 250 MB per environment, 3 preview environments, 2 custom domains, and **managed Functions APIs** (HTTP only). There is no SLA.
- Standard adds "bring your own Functions app", custom auth and private endpoints. The Dedicated plan was retired on 31 Oct 2025.
- The managed API is the natural home for `/api/negotiate`, which returns the Web PubSub client URL with the right groups for the selected profile.

### 8. Credits and cost control

- **Azure free account:** $200 credit for 30 days, 12 months of popular services, and 65+ always-free services. These include Functions (1M requests), Cosmos DB (1,000 RU/s + 25 GB), and Container Apps (180,000 vCPU-s, 360,000 GiB-s and 2M requests per month).
- **Azure for Students:** $100 credit for 12 months with no credit card, for full-time university students only.
- **Hackathon credits:** not verified. Check the Innovation Studio hackathon page (unverified).
- **Budgets alert but do not stop resources.** Cost data lands within 8–24 h and budgets are evaluated every 24 h, so budgets are a safety net, not a kill switch. Set alerts at 50/80/100% of actual and forecast spend. Connect an **action group** to get phone push alerts.
- **Habits:**
  - Put everything in one resource group and delete it after the event.
  - Keep GPU apps and jobs at `minReplicas: 0`.
  - Use the emulator during dev.
  - Don't leave an ASA job running overnight.

### 9. Latency budget (reasoning, sourced numbers only)

The sourced figures are:
- **Cosmos DB** point read: < 10 ms (SLA, provisioned).
- **Web PubSub**: stays low under 70% load. The benchmark ceiling is p99 < 1 s.
- **KEDA** polling: 30 s.
- **ASA** windows: emit at the end of the window.
- **Flex Consumption** host init: up to a 30 s timeout.

**Event Hubs end-to-end latency has no Microsoft Learn figure.** Secondary sources cite single-digit ms for Premium (unverified). So:

1. The fixed costs (broker + push) are small next to two things we control: **LLM generation time** and **windowing delay**.
2. Avoid every "wait for a timer" component on the hot path: scale-from-zero, ASA window ends, and the 30 s load-balancing interval when several consumers start.
3. For Explain, send the **numeric cue first**, then follow up with the narrative text under the same `cue_id`. The overlay never waits on the model.
4. **Measure, don't guess.** Stamp `t_emit` in the producer, `t_cue` in the worker and `t_render` in the browser, and show the p50/p95 on a debug HUD. That gives us our own sourced number for the pitch.

## So what for us

- **Stages:** Ingest → Interpret → Render, plus the hooks for Explain and Personalise.
- **A TwinCast:** the simulator and the CV auto-eventer both produce into one Event Hub, on separate hubs or with a `source` field. A second consumer group grades CV events against ground truth. ACA Jobs and serverless GPU cover the CV/render work. Web PubSub carries the overlay cues.
- **B Speed Trap:** threshold checks belong in the Python worker, using sliding windows over frame events. Send whole frames per event to stay under the 1,000 events/s per TU limit.
- **C One Number:** maps directly onto a `m_{match}_metric_{name}` Web PubSub group.
- **F Graphics Desk:** producer console = a client with `sendToGroup` rights on a `desk` group. Take/hold commands flow back to the worker through an upstream event handler (unverified details) or a tiny HTTP API.
- **Personalise ideas (10 Story Time, 12 Jargon Buster, language modes):** each is just another group variant rendered by the worker.

**Recommended build for 2 people × 2 weeks:**

1. **Days 1–2:** emulator + Azurite in Docker Compose. `producer.py` replays a seeded synthetic match. `worker.py` reads, computes windows and prints cue JSON.
2. **Days 3–4:** create the Azure resources in one resource group:
   - Event Hubs Standard with 1 TU, 4 partitions and consumer groups `worker`, `grader`, `replay`
   - Web PubSub Free_F1
   - Cosmos DB with free tier on
   - SWA Free with a `/api/negotiate` managed function
   - ACA environment running the worker at `minReplicas: 1`, `maxReplicas: 1`
3. **Week 2:** add the Foundry call for Explain using a numeric-first, text-follow pattern, plus Cosmos persistence and profile groups. Upgrade Web PubSub to Standard 1 unit at least 2 days before the demo. Add Capture only if replay-from-blob is needed.
4. **Skip:** Stream Analytics, Redis and Functions Event Hubs triggers. That leaves fewer moving parts and faster debugging.

## Reuse: code & links

`pip install azure-eventhub azure-messaging-webpubsubservice aiohttp` (aiohttp provides the async HTTP transport)

**Producer: JSON match events (works against the emulator or Azure)**

```python
# producer.py
import asyncio, json, os, random, time
from azure.eventhub import EventData
from azure.eventhub.aio import EventHubProducerClient

CONN = os.environ["EVENTHUB_CONN"]  # emulator: Endpoint=sb://localhost;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=SAS_KEY_VALUE;UseDevelopmentEmulator=true;
HUB = os.environ.get("EVENTHUB_NAME", "match-events")
MATCH_ID = "SYN-0001"  # synthetic only

def make_event(seq: int) -> dict:
    etype = random.choice(["pass", "pass", "pass", "tackle", "shot", "pressure"])
    return {
        "event_id": f"{MATCH_ID}-{seq}", "match_id": MATCH_ID, "seq": seq,
        "type": etype, "match_clock_ms": seq * 1500, "team": random.choice(["HOME", "AWAY"]),
        "player_id": f"P{random.randint(1, 11)}", "x": round(random.uniform(0, 105), 1),
        "y": round(random.uniform(0, 68), 1), "t_emit": time.time(), "synthetic": True,
    }

async def main() -> None:
    producer = EventHubProducerClient.from_connection_string(CONN, eventhub_name=HUB)
    async with producer:
        seq = 0
        while True:
            # same partition_key => all events of one match stay in order on one partition
            batch = await producer.create_batch(partition_key=MATCH_ID)
            for _ in range(5):
                try:
                    batch.add(EventData(json.dumps(make_event(seq))))
                    seq += 1
                except ValueError:  # batch full (1 MB on Standard / emulator)
                    break
            await producer.send_batch(batch)
            await asyncio.sleep(1.0)

if __name__ == "__main__":
    asyncio.run(main())
```

**Async consumer + windowed stat + publish to Web PubSub groups**

```python
# worker.py
import asyncio, json, os, time
from collections import deque
from azure.eventhub.aio import EventHubConsumerClient
from azure.messaging.webpubsubservice.aio import WebPubSubServiceClient

EH_CONN = os.environ["EVENTHUB_CONN"]
HUB = os.environ.get("EVENTHUB_NAME", "match-events")
WPS_CONN = os.environ["WEBPUBSUB_CONN"]
WINDOW_MS = 5 * 60 * 1000          # 5-minute sliding window on match clock

window: deque = deque()             # (match_clock_ms, team) for passes
wps = WebPubSubServiceClient.from_connection_string(WPS_CONN, hub="match")

def pass_share(now_ms: int) -> dict:
    while window and window[0][0] < now_ms - WINDOW_MS:
        window.popleft()
    home = sum(1 for _, t in window if t == "HOME")
    total = len(window) or 1
    return {"HOME": round(100 * home / total), "AWAY": round(100 * (total - home) / total)}

async def publish(ev: dict, share: dict) -> None:
    base = {"cue_id": f"cue-{ev['event_id']}", "match_clock": ev["match_clock_ms"], "ttl_ms": 6000,
            "metric": "pass_share_5m", "value": share, "evidence_ids": [ev["event_id"]],
            "source": "synthetic", "t_emit": ev["t_emit"], "t_cue": time.time()}
    variants = {
        f"m_{ev['match_id']}_analyst_en": {**base, "text": f"Pass share last 5': HOME {share['HOME']}% / AWAY {share['AWAY']}%"},
        f"m_{ev['match_id']}_casual_en":   {**base, "text": f"HOME have had the ball {share['HOME']}% of the time lately"},
    }
    await asyncio.gather(*(wps.send_to_group(g, msg, content_type="application/json") for g, msg in variants.items()))

async def on_event(partition_context, event) -> None:
    ev = json.loads(event.body_as_str(encoding="UTF-8"))
    if ev["type"] == "pass":
        window.append((ev["match_clock_ms"], ev["team"]))
        await publish(ev, pass_share(ev["match_clock_ms"]))

async def main() -> None:
    # No checkpoint_store => in-memory checkpoints, single consumer (fine for one replica)
    client = EventHubConsumerClient.from_connection_string(EH_CONN, consumer_group="$Default", eventhub_name=HUB)
    try:
        async with client:
            await client.receive(on_event=on_event, starting_position="@latest")
    finally:
        await wps.close()

if __name__ == "__main__":
    asyncio.run(main())
```

**Negotiate endpoint (server) and browser subscribe (TS)**

```python
# inside an HTTP handler (SWA managed function or ACA API)
token = await wps.get_client_access_token(
    groups=[f"m_{match_id}_{mode}_{lang}"],
    roles=[f"webpubsub.joinLeaveGroup.m_{match_id}_analyst_{lang}",
           f"webpubsub.joinLeaveGroup.m_{match_id}_casual_{lang}"],
    minutes_to_expire=60)
return {"url": token["url"]}
```

```ts
import { WebPubSubClient } from "@azure/web-pubsub-client";
const { url } = await (await fetch(`/api/negotiate?mode=casual`)).json();
const client = new WebPubSubClient(url);
client.on("group-message", (e) => scheduleOverlay(e.message.data)); // cue JSON
await client.start();
```

**Emulator docker-compose:** copy `docker-compose.yaml` + `config.json` from the "Test locally with the emulator" page (link below). Set `ACCEPT_EULA="Y"` in `.env`.

**Repos/samples:**
- Emulator installer: https://github.com/Azure/azure-event-hubs-emulator-installer
- Python async send sample: https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/eventhub/azure-eventhub/samples/async_samples/send_async.py
- Flex Consumption samples: https://github.com/Azure-Samples/azure-functions-flex-consumption-samples
- Kafka on Event Hubs samples: https://github.com/Azure/azure-event-hubs-for-kafka

## Sources

- Azure Event Hubs quotas and limits — https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-quotas — accessed 20 Oct 2026
- Azure Event Hubs emulator overview — https://learn.microsoft.com/en-us/azure/event-hubs/overview-emulator — accessed 20 Oct 2026
- Test locally with the Event Hubs emulator — https://learn.microsoft.com/en-us/azure/event-hubs/test-locally-with-event-hub-emulator — accessed 20 Oct 2026
- Send and receive events using Python — https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-python-get-started-send — accessed 20 Oct 2026
- EventHubConsumerClient (aio) API reference — https://learn.microsoft.com/en-us/python/api/azure-eventhub/azure.eventhub.aio.eventhubconsumerclient — accessed 20 Oct 2026
- Apache Kafka protocol support in Event Hubs — https://learn.microsoft.com/en-us/azure/event-hubs/azure-event-hubs-apache-kafka-overview — accessed 20 Oct 2026
- Event Hubs Capture overview — https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-capture-overview — accessed 20 Oct 2026
- Stream Analytics windowing functions — https://learn.microsoft.com/en-us/azure/stream-analytics/stream-analytics-window-functions — accessed 20 Oct 2026
- Stream Analytics streaming units — https://learn.microsoft.com/en-us/azure/stream-analytics/stream-analytics-streaming-unit-consumption — accessed 20 Oct 2026
- Azure Functions Flex Consumption plan — https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-plan — accessed 20 Oct 2026
- Event Hubs trigger for Azure Functions — https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-event-hubs-trigger — accessed 20 Oct 2026
- Scaling in Azure Container Apps — https://learn.microsoft.com/en-us/azure/container-apps/scale-app — accessed 20 Oct 2026
- KEDA Azure Event Hubs scaler — https://keda.sh/docs/2.17/scalers/azure-event-hub/ — accessed 20 Oct 2026
- Serverless GPUs in Azure Container Apps — https://learn.microsoft.com/en-us/azure/container-apps/gpu-serverless-overview — accessed 20 Oct 2026
- Azure subscription service limits (Web PubSub, SignalR, Functions) — https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/azure-subscription-service-limits — accessed 20 Oct 2026
- Azure Web PubSub pricing — https://azure.microsoft.com/en-us/pricing/details/web-pubsub/ — accessed 20 Oct 2026
- Scale an Azure Web PubSub instance — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/howto-scale-manual-scale — accessed 20 Oct 2026
- Web PubSub FAQ (vs SignalR) — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/resource-faq — accessed 20 Oct 2026
- Web PubSub Python server SDK — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/reference-server-sdk-python — accessed 20 Oct 2026
- WebPubSubServiceClient (aio) API reference — https://learn.microsoft.com/en-us/python/api/azure-messaging-webpubsubservice/azure.messaging.webpubsubservice.aio.webpubsubserviceclient — accessed 20 Oct 2026
- Generate client access URL — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/howto-generate-client-access-url — accessed 20 Oct 2026
- PubSub among clients (JS client SDK) — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/quickstarts-pubsub-among-clients — accessed 20 Oct 2026
- Web PubSub performance guide — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/concept-performance — accessed 20 Oct 2026
- Create a Web PubSub resource (Free_F1 SKU) — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/howto-develop-create-instance — accessed 20 Oct 2026
- Cosmos DB lifetime free tier — https://learn.microsoft.com/en-us/azure/cosmos-db/free-tier — accessed 20 Oct 2026
- Cosmos DB serverless — https://learn.microsoft.com/en-us/azure/cosmos-db/serverless — accessed 20 Oct 2026
- Cosmos DB provisioned vs serverless — https://learn.microsoft.com/en-us/azure/cosmos-db/throughput-serverless — accessed 20 Oct 2026
- What is Azure Managed Redis — https://learn.microsoft.com/en-us/azure/redis/overview — accessed 20 Oct 2026
- Azure Cache for Redis retirement FAQ — https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/retirement-faq — accessed 20 Oct 2026
- Static Web Apps hosting plans — https://learn.microsoft.com/en-us/azure/static-web-apps/plans — accessed 20 Oct 2026
- Static Web Apps quotas — https://learn.microsoft.com/en-us/azure/static-web-apps/quotas — accessed 20 Oct 2026
- Azure free account — https://azure.microsoft.com/en-us/pricing/purchase-options/azure-account — accessed 20 Oct 2026
- Azure for Students — https://azure.microsoft.com/en-us/free/students — accessed 20 Oct 2026
- Create and manage budgets — https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets — accessed 20 Oct 2026
- What is Microsoft Foundry — https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry — accessed 20 Oct 2026
