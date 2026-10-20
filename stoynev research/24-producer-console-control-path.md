# 24 — Two-way control: producer console take/hold/kill, viewer mode switching, and cue scheduling

_Accessed/compiled: 20 Oct 2026 · Priority area: Render + Personalise (control path back from the browser to the cue engine; human in the loop)_

## TL;DR

- **Send commands as Web PubSub custom events, not group messages.** A client with no roles can still send `{"type":"event","event":"cmd",...}`. The service POSTs it to our FastAPI webhook as a CloudEvent (`ce-type: azure.webpubsub.user.cmd`, plus `ce-userId` and `ce-signature`). The HTTP response body goes back to that same client as a `server-message`. That gives us an authenticated request/ack path with no extra API. **Do not** give the console `sendToGroup` rights on programme groups, or it could skip the scheduler and the audit log.
- **Gotcha: a non-2xx reply to a user event drops the client's connection.** Reject a forbidden or badly timed TAKE with `200 {"ok":false,"err":...}`, never 403. User events are *blocking*: the service waits for our reply. So the handler only enqueues work. It never calls an LLM inline.
- **Idempotency in two layers.** Web PubSub dedupes a repeated `ackId` on the same connection (`Duplicate` error). That does not help after a reconnect, which brings a new connection ID. So every command also carries a UUID `cmd_id`, and the server caches its ack. Programme cues carry a per-match `seq`, so viewers drop duplicates and stale messages.
- **Scheduler = salience heap + one cue per screen region + cooldowns + TTL + pre-emption.** States: `proposed → ready → on_air → done`, plus `expired` and `killed`. A goal evicts a lower-priority cue and skips cooldowns. HOLD stops auto-take and auto-clear. A tested ~75-line asyncio version is below.
- **Clock sync:** NTP-style offset `((t1−t0)+(t2−t3))/2` (RFC 5905), taken from the lowest-delay of about 8 probes (Cristian's idea), measured on `performance.timeOrigin + performance.now()` (monotonic). Late cues are shown shortened if at least 2 s of dwell remains, otherwise dropped. Goals are always shown (thresholds are our guesses).

## Findings

### 1. What Azure Web PubSub gives us for the control path

| Need | Web PubSub feature (verified in docs) |
|---|---|
| Client → server command | `event` request in `json.webpubsub.azure.v1`. "Not specified" role = "The client can send event requests." Upstream gets `ce-type: azure.webpubsub.user.<event_name>` with JSON body |
| Server → client ack | Upstream `200` response. With `Content-Type: application/json`, the client receives it as `dataType=json` from `server` |
| Who sent it | `ce-userId` (from the JWT `sub`) and `ce-connectionId`. `ce-signature` = `Hex(HMAC_SHA256(accessKey, connectionId))` for primary and secondary keys |
| Webhook registration | URL template (supports `{hub}`, `{event}`, Key Vault refs). Auth: anonymous, `?code=`, or Microsoft Entra. CloudEvents abuse protection: `OPTIONS` with `WebHook-Request-Origin`, reply `WebHook-Allowed-Origin` |
| Blocking semantics | `connect` and user events are blocking. `connected` and `disconnected` are not. **Any non-success status on a user event drops the connection** |
| Roles | `webpubsub.joinLeaveGroup[.<group>]`, `webpubsub.sendToGroup[.<group>]`, plus wildcard `webpubsub.joinLeaveGroups.<pattern>` / `sendToGroups.<pattern>` (`*` stops at `.`, `**` crosses it, max five `*`). Wildcards work in tokens but not yet in runtime REST grants |
| Token | `get_client_access_token(user_id=..., roles=[...], groups=[...], minutes_to_expire=...)`. Custom JWT claims are forwarded as `claims` in the `connect` event |
| Dedupe | `ackId` is "unique within a client with the same connection ID". A repeat gets `Duplicate` |
| Ordering / loss | The JS client defaults to `json.reliable.webpubsub.azure.v1`. Messages carry `sequenceId` and the client sends `sequenceAck`. Recovery reuses the connection ID if it reconnects within **30 s**. Otherwise it is a new connection, and only groups the *client* joined are auto-rejoined |
| Server-side targeting | `send_to_all` / `send_to_group` / `send_to_user` take an OData `filter` over `userId`, `connectionId` and `groups` only (for example `'m42.casual.en' in groups and userId ne 'x'`). Keep it under about 100 clauses |
| Local dev | `awps-tunnel` (preview) tunnels webhooks to localhost. Set the URL template to `tunnel:///eventhandler` |
| Request/response API | `client.invokeEvent(...)` exists in the JS client README as **preview**. We use `sendEvent` + `cmd_id` correlation instead. How invoke maps upstream is unverified |

**Socket.IO option.** Web PubSub for Socket.IO is a managed Socket.IO host ("more than 100,000 client connections out of the box"). `fetchSockets` is local only, and `serverSideEmit` / `serverSideEmitWithAck` are unsupported. Its samples are Node-centric, and our server is Python (Python server support is unverified). Native Web PubSub plus the event handler already gives acks, so skip Socket.IO.

**FastAPI WebSockets as a fallback.** FastAPI's own `@app.websocket` works for a laptop-only demo. Use `WebSocketException(code=status.WS_1008_POLICY_VIOLATION)` for a bad token. The docs warn that the in-memory connection list "will only work with a single process". Fine for a judge demo on one replica, not beyond.

### 2. Broadcast playout vocabulary we should copy

- **Sofie (NRK, open source):** the *Part* playing is "On Air". The part cued to play is "Next". A **TAKE** plays the Next part. *AdLib* pieces are "intended to be manually triggered by the user". Before playback, parts are copied into `PartInstances`, so live edits cannot surprise the director. That is the "as played" vs "as planned" record. Sofie's **Hold** is a special split-edit take, *not* "pause". Our HOLD means "freeze this cue: don't auto-take it and don't auto-clear it". The README should say so to avoid confusion. Sofie access levels separate `studio` (operate playout) from `configure` and `developer`. That is a good model for our roles.
- **CasparCG AMCP:** addresses are `channel-layer` (for example `1-20`). `LOADBG` preloads, then `PLAY` moves it to the foreground (a preview → program split). `CG STOP` animates out and `CG REMOVE` removes with no out-animation. `CLEAR 1` empties the whole channel. Replies: `201`/`202` OK, `400`–`404` client error.
- **SPX-GC open-source API (`routes-api-v1.js`):** `/api/v1/item/play`, `/item/continue` (needs template support), `/item/stop`, `/rundown/focusNext`, `/rundown/stopAllLayers` (animate out), and `/api/v1/panic`. Panic is a "Force clear to all output layers without out-animations… for emergency situations only". `directplayout` returns 501 in the free edition.

**Mapping to our commands.** `NEXT` = arm the cue in the console preview (Sofie Next / CasparCG LOADBG). `TAKE` = play it (`CG PLAY`, SPX play). The scheduler's `CLEAR` at TTL = `CG STOP` (animated). `KILL` = `CG REMOVE` (cut). `KILL_ALL` = SPX panic / AMCP `CLEAR`.

### 3. Message design (v1)

```jsonc
// console/viewer -> server   (Web PubSub event "cmd")
{"v":1,"type":"cmd","cmd":"TAKE","cmd_id":"6f1c…uuid","cue_id":"c-0193","match":"m42","expect_rev":17,"client_ms":1760968800123.4}
// server -> that client       (HTTP 200 body of the upstream call)
{"type":"ack","v":1,"cmd_id":"6f1c…","ok":false,"err":"bad_state","server_ms":1760968800171.0}
// server -> programme groups  (send_to_group, serialised through ONE asyncio publish queue)
{"v":1,"type":"cue","action":"TAKE|CLEAR|KILL","cue_id":"c-0193","seq":1043,"show_at_ms":1760968801000,
 "ttl_ms":6000,"layout":"strap","preempt":false,"text":"…","evidence":["e-881"],"by":"producer:ana"}
```

- **Commands:** producer `TAKE`, `NEXT`, `HOLD`, `KILL`, `KILL_ALL`. Viewer `SET_MODE`, `SET_PLAYER_FOCUS`, `SET_LANGUAGE`. Unknown `cmd` returns `ok:false`, never a non-2xx.
- **Versioning:** an integer `v` (major). Additive fields are ignored by older clients. A different major gets `err:"version"`. `expect_rev` (rundown revision) gives optimistic concurrency, so two producers can't both TAKE into one slot (not in the snippet; add it if two people run the console).
- **Ordering:** REST publishes sent at the same time can arrive out of order. So all fan-out goes through one queue and stamps a per-match `seq`. Clients keep the last `seq` per `cue_id`, so a late TAKE can't resurrect a killed cue.
- **Personalisation: groups vs server-side filtering.** Groups are named `m42.<mode>.<lang>` (for example `m42.casual.bg`) and `m42.player.<id>` for focus tags. The viewer token gets `webpubsub.joinLeaveGroups.m42.**`, so a mode switch is a client-side leave/join with no server round trip. The client then sends `SET_MODE` so the server knows to *start rendering* that variant. That matters for languages, where each variant costs an LLM or Translator call. We rejected the alternatives. (a) Server-side `add_connection_to_group`: adds a hop, and server-joined groups are not auto-rejoined after a reconnect. (b) OData filters: they only see userId, connectionId and groups, so they are still group-based. (c) Sending everything and filtering in the browser: it burns the outbound-message quota (Free_F1 is 20k/day, per research 01).

### 4. Cue scheduler and state machine

```
proposed ──(fact-check + grammar gate, research 11)──► ready ──TAKE (auto or producer)──► on_air ──TTL / replaced──► done
   ready ──stale_at passed──► expired        ready|on_air ──KILL──► killed        HOLD toggles held flag (no auto-take / auto-clear)
```

Rules (the region map and cooldowns come from the research 11 grammar; all numbers are our guesses):

1. Max-heap by `salience`, with an insertion counter as tie-break (heapq docs pattern). Lazy deletion of taken, killed and expired entries.
2. **Layout exclusivity:** one cue per region (`lower` holds `strap`/`compare`; `upper_right` holds `pop`/`prob`).
3. **Cooldown per layout.** A manual TAKE ignores cooldown, because the producer is the boss.
4. **TTL:** `stale_at` for un-aired cues (a "great pass" strap is useless 20 s later). `ttl_ms` for on-air dwell.
5. **Pre-emption:** a `preempt` cue (goal, red card) evicts a non-preempt cue in its region and skips cooldown.
6. **Modes:** `auto_take=True` for viewer streams. `auto_take=False` for **F Graphics Desk**, where AI cues wait as `ready` until a human TAKEs them.

### 5. Clock sync and late cues

- Each probe records `t0` (client send), `t1` / `t2` (server receive and send) and `t3` (client receive). Offset θ = ½[(t1−t0)+(t2−t3)] and delay δ = (t3−t0)−(t2−t1), as in RFC 5905 §8. With symmetric paths, the true offset lies within θ ± δ/2 (our derivation). So keep the **minimum-delay** sample. Cristian notes that offset and jitter are reduced "by selecting suitable RTT". Our probe goes browser → Web PubSub → webhook and back, so RTT is larger and less symmetric than plain NTP. Measure it rather than assume it.
- Use `performance.timeOrigin + performance.now()`. MDN says `Date.now()` "may have been impacted by system and user clock adjustments", while `performance.now()` is monotonic.
- **Video vs wall clock:** if the overlay sits on our own rendered video (TwinCast), schedule on the media clock (`requestVideoFrameCallback`, research 04). The server offset is for live web overlays, producer countdowns and latency metrics (`proposal → take → on screen`).
- **Late policy (our guesses):** if up to 250 ms late, show as is. If later, show for the remaining TTL when at least 2 s is left, otherwise drop and log `late_drop`. Goals are always shown in full.

### 6. Security and audit

- `/api/negotiate` sits behind our login and mints the `userId` as `producer:<name>` or `viewer:<anon-id>`, with a short `minutes_to_expire`. The console token has **no** `sendToGroup` role. Viewers get only `joinLeaveGroups.m42.**`.
- The webhook verifies `ce-signature` with a constant-time compare and checks the role prefix of `ce-userId` per command. Use `?code=` or Entra auth on the webhook URL. With Entra, the identity needs both `clientConnection/generateToken/action` and `clientConnection/write`. The only built-in role with both is the broad *Web PubSub Service Owner*.
- **Audit log (judging asset).** Write one append-only document per command and per automatic transition: `{ts_server, match_clock, user, cmd, cue_id, from_state, to_state, ok, err, salience, ms_in_queue}`. Store it in Cosmos, partitioned by `match_id`. In the demo, show an "as played" strip (the Sofie idea) and two numbers: **AI-proposal acceptance rate** and **median propose→take time**. That is concrete evidence of a human in the loop.

## So what for us

Stages: **Render** (scheduler, programme fan-out) and **Personalise** (viewer mode/language/player groups). This is the core of **F Graphics Desk**. It also gives **A TwinCast** a credible "producer approves AI cues" story and a clean `auto_take` switch for viewer streams. **C One Number** and **B Speed Trap** use the same `SET_MODE` / `SET_PLAYER_FOCUS` path.

Recommendation:
1. One Web PubSub hub `studio`, one event handler `/eventhandler` on the existing ACA worker, the same process as the scheduler (min 1 replica). Develop with `awps-tunnel`.
2. Use the scheduler below with `auto_take=False` for the console group and `True` for viewer groups.
3. Use `cmd_id` and `seq` from day one. They cost about 10 lines and prevent double-takes on reconnect, which judges *will* see if the Wi-Fi blips.
4. Ship the audit strip and the two metrics in the demo video.
5. Do not use Socket.IO or a second WebSocket server.

## Reuse: code & links

**Cue scheduler** (Python 3.12, standard library only). We tested it locally: priority order, region lock, cooldown wait, stale expiry, goal pre-emption, manual NEXT/TAKE, HOLD surviving TTL, KILL_ALL, and a double TAKE returning `False`.

```python
# cue_scheduler.py: priority queue by salience, one cue per screen region, cooldowns, TTL, goal pre-emption
import asyncio, heapq, itertools, time
from dataclasses import dataclass

REGION = {"tag": "player", "pop": "upper_right", "prob": "upper_right",       # from research 11
          "strap": "lower", "compare": "lower", "pitch": "full", "summary": "full"}
COOLDOWN_S = {"tag": 20, "pop": 45, "strap": 30, "compare": 90, "pitch": 300, "prob": 60}

@dataclass(eq=False)
class Cue:
    cue_id: str; layout: str; salience: float; ttl_ms: int
    stale_at: float               # monotonic s; an un-aired cue is worthless after this
    preempt: bool = False         # goal / red card: jumps cooldowns, evicts non-preempt cue
    state: str = "ready"          # ready -> on_air -> done | expired | killed
    held: bool = False            # HOLD: never auto-taken, never auto-cleared
    off_at: float = 0.0

class CueScheduler:
    def __init__(self, publish, auto_take=True):
        self.publish, self.auto = publish, auto_take      # publish(action, cue, by) -> awaitable
        self.heap, self.seq = [], itertools.count()
        self.by_id: dict[str, Cue] = {}
        self.on_air: dict[str, Cue] = {}                  # region -> cue (layout exclusivity)
        self.last: dict[str, float] = {}                  # layout -> last take time
        self.next_id: str | None = None                  # NEXT = armed in console preview
        self.wake = asyncio.Event()

    def propose(self, c: Cue):
        self.by_id[c.cue_id] = c
        heapq.heappush(self.heap, (-c.salience, next(self.seq), c))
        self.wake.set()

    def eligible(self, c: Cue, now: float) -> bool:
        busy = self.on_air.get(REGION[c.layout])
        cooled = now - self.last.get(c.layout, -1e9) >= COOLDOWN_S.get(c.layout, 0)
        return (busy is None or (c.preempt and not busy.preempt)) and (cooled or c.preempt)

    async def take(self, c: Cue, now: float, by="auto"):
        if old := self.on_air.get(REGION[c.layout]): await self.clear(old, "done", by)
        c.state, c.off_at = "on_air", now + c.ttl_ms / 1000
        self.on_air[REGION[c.layout]], self.last[c.layout] = c, now
        await self.publish("TAKE", c, by)

    async def clear(self, c: Cue, state: str, by="auto"):
        if self.on_air.get(REGION[c.layout]) is c: del self.on_air[REGION[c.layout]]
        c.state = state
        await self.publish("CLEAR" if state == "done" else "KILL", c, by)

    async def command(self, cmd: str, cue_id: str | None, by: str) -> bool:
        now, c = time.monotonic(), self.by_id.get(cue_id or self.next_id or "")
        if cmd == "NEXT" and c and c.state == "ready": self.next_id = c.cue_id
        elif cmd == "TAKE" and c and c.state == "ready": await self.take(c, now, by)
        elif cmd == "HOLD" and c and c.state in ("ready", "on_air"): c.held = not c.held
        elif cmd == "KILL" and c and c.state == "on_air": await self.clear(c, "killed", by)
        elif cmd == "KILL" and c and c.state == "ready": c.state = "killed"   # reject proposal
        elif cmd == "KILL_ALL":
            for x in list(self.on_air.values()): await self.clear(x, "killed", by)
        else: return False                                 # wrong state -> negative ack
        self.wake.set(); return True

    async def run(self):
        while True:
            now, keep = time.monotonic(), []
            for c in list(self.on_air.values()):          # TTL expiry of on-air cues
                if not c.held and now >= c.off_at: await self.clear(c, "done")
            while self.heap:
                item = heapq.heappop(self.heap); c = item[2]
                if c.state != "ready": continue            # lazy delete (taken/killed)
                if now >= c.stale_at and not c.held: c.state = "expired"; continue
                if self.auto and not c.held and self.eligible(c, now): await self.take(c, now)
                else: keep.append(item)
            for item in keep: heapq.heappush(self.heap, item)
            self.wake.clear()
            try: await asyncio.wait_for(self.wake.wait(), timeout=0.1)
            except asyncio.TimeoutError: pass
```

**Web PubSub upstream handler** (FastAPI). It compiles, and we unit-tested the signature check. We did not run it against a live hub. Register the URL template `https://<aca-app>/eventhandler`, user events `cmd,time`, and system event `connect` if needed.

```python
# upstream.py: Web PubSub event handler (CloudEvents HTTP binding) for producer + viewer commands
import hashlib, hmac, os, time
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from cue_scheduler import CueScheduler

app = FastAPI()
KEYS = [k for k in (os.getenv("WPS_KEY1"), os.getenv("WPS_KEY2")) if k]   # primary + secondary
WPS_HOST = os.environ["WPS_HOST"]                    # e.g. berbata.webpubsub.azure.com
PRODUCER = {"TAKE", "NEXT", "HOLD", "KILL", "KILL_ALL"}
VIEWER = {"SET_MODE", "SET_PLAYER_FOCUS", "SET_LANGUAGE"}
acks: dict[str, dict] = {}                           # cmd_id -> ack (idempotent retries)
scheduler: CueScheduler                              # created at startup with publish=fan_out

def signed(conn_id: str, header: str) -> bool:       # ce-signature: sha256=<hex>,sha256=<hex>
    sigs = [s.strip().removeprefix("sha256=") for s in header.split(",")]
    good = [hmac.new(k.encode(), conn_id.encode(), hashlib.sha256).hexdigest() for k in KEYS]
    return any(hmac.compare_digest(s, g) for s in sigs for g in good)

@app.options("/eventhandler")                        # abuse-protection handshake
async def validate(request: Request):
    if request.headers.get("webhook-request-origin") != WPS_HOST:
        return Response(status_code=400)
    return Response(headers={"WebHook-Allowed-Origin": WPS_HOST})

@app.post("/eventhandler")
async def events(request: Request):
    h = request.headers
    if not signed(h.get("ce-connectionid", ""), h.get("ce-signature", "")):
        return Response(status_code=401)             # non-2xx drops the connection: fine here
    if h.get("ce-type") == "azure.webpubsub.sys.connect":
        return Response(status_code=204)             # roles/groups already in the JWT
    user, event = h.get("ce-userid", ""), h.get("ce-eventname")
    if event == "time":                              # clock-sync probe: echo t0, add t1/t2
        t1 = time.time() * 1000
        body = await request.json()
        return JSONResponse({"type": "time", "t0": body["t0"], "t1": t1, "t2": time.time() * 1000})
    if event != "cmd":
        return Response(status_code=204)
    m = await request.json()
    if m.get("v") != 1:
        return JSONResponse({"type": "ack", "cmd_id": m.get("cmd_id"), "ok": False, "err": "version"})
    if (cid := m["cmd_id"]) in acks:                 # retry of a command we already applied
        return JSONResponse(acks[cid] | {"dup": True})
    role = user.split(":", 1)[0]                     # userId minted as "producer:ana" / "viewer:x"
    if m["cmd"] in PRODUCER and role != "producer":
        ok, err = False, "forbidden"                 # 200 + ok:false, NOT 403 (403 drops socket)
    elif m["cmd"] in PRODUCER:
        ok = await scheduler.command(m["cmd"], m.get("cue_id"), by=user)
        err = None if ok else "bad_state"
    elif m["cmd"] in VIEWER:                         # record preference; client joins groups itself
        ok, err = True, None                         # e.g. start rendering a new language variant
    else:
        ok, err = False, "unknown_cmd"
    ack = {"type": "ack", "v": 1, "cmd_id": cid, "ok": ok, "err": err, "server_ms": time.time() * 1000}
    acks[cid] = ack
    # audit: append {ts, user, cmd, cue_id, ok, err} to Cosmos container "audit" (pk = match_id)
    return JSONResponse(ack)
```

**Clock maths** (TypeScript). The self-test passes on Node 24: offset is recovered exactly from the symmetric sample, and the late-cue policy gives show / shorten / drop / goal-override.

```ts
// clock.ts: pure helpers
export type Sample = { t0: number; t1: number; t2: number; t3: number };
export const now = () => performance.timeOrigin + performance.now();   // monotonic epoch ms

// NTP on-wire maths (RFC 5905 s.8) on the lowest-delay sample (Cristian: pick the best RTT)
export function estimateOffset(samples: Sample[]): { offset: number; delay: number } {
  const scored = samples.map(s => ({
    offset: ((s.t1 - s.t0) + (s.t2 - s.t3)) / 2,
    delay: (s.t3 - s.t0) - (s.t2 - s.t1),
  }));
  return scored.reduce((a, b) => (b.delay < a.delay ? b : a));
}

// Late-cue policy (thresholds are our guesses): on time, shortened, or dropped
export function planCue(showAtMs: number, ttlMs: number, serverNow: number, preempt = false,
                        minDwellMs = 2000, graceMs = 250) {
  const late = serverNow - showAtMs;
  if (late <= graceMs) return { action: "show", inMs: Math.max(0, -late), ttlMs };
  if (preempt) return { action: "show", inMs: 0, ttlMs };              // goals: always full
  const left = ttlMs - late;
  return left >= minDwellMs ? { action: "show", inMs: 0, ttlMs: left } : { action: "drop", late };
}
```

**Console and viewer client** (`@azure/web-pubsub-client`). Not run against a live hub.

```ts
// control.ts: console + viewer side (not run against a live hub; clock.ts maths is tested)
import { WebPubSubClient } from "@azure/web-pubsub-client";
import { estimateOffset, planCue, now, type Sample } from "./clock";

const client = new WebPubSubClient({   // /api/negotiate checks login, mints userId "producer:ana"
  getClientAccessUrl: async () => (await (await fetch("/api/negotiate")).json()).url,
});
const pending = new Map<string, (ack: any) => void>();
const samples: Sample[] = [];
let offset = 0;
export const serverNow = () => now() + offset;

client.on("server-message", (e) => {       // upstream HTTP response bodies arrive here
  const m = e.message.data as any;
  if (m.type === "ack") { pending.get(m.cmd_id)?.(m); pending.delete(m.cmd_id); }
  if (m.type === "time") {
    samples.push({ t0: m.t0, t1: m.t1, t2: m.t2, t3: now() });
    if (samples.length > 8) samples.shift();
    offset = estimateOffset(samples).offset;
  }
});

// Command with app-level ack + retry; the same cmd_id on every retry lets the server dedupe
export function send(cmd: string, extra: object = {}, timeoutMs = 3000, tries = 3) {
  const msg = { v: 1, type: "cmd", cmd, cmd_id: crypto.randomUUID(), client_ms: now(), ...extra };
  return new Promise((resolve, reject) => {
    const attempt = async (n: number) => {
      pending.set(msg.cmd_id, resolve);
      await client.sendEvent("cmd", msg, "json");
      setTimeout(() => {
        if (!pending.has(msg.cmd_id)) return;
        n + 1 < tries ? attempt(n + 1) : (pending.delete(msg.cmd_id), reject(new Error("no ack")));
      }, timeoutMs);
    };
    attempt(0);
  });
}

const probe = () => client.sendEvent("time", { t0: now() }, "json");
await client.start();
for (let i = 0; i < 8; i++) { await probe(); await new Promise((r) => setTimeout(r, 200)); }
setInterval(probe, 30_000);                // re-sync for drift (interval is our choice)

// Producer buttons: send("NEXT", { cue_id }), send("TAKE"), send("HOLD", { cue_id }), send("KILL_ALL")

// Viewer personalisation: switch groups on the client, then tell the server
let joined: string[] = [];
export async function setMode(match: string, mode: string, lang: string) {
  const want = [`${match}.${mode}.${lang}`];
  for (const g of joined.filter((g) => !want.includes(g))) await client.leaveGroup(g);
  for (const g of want.filter((g) => !joined.includes(g))) await client.joinGroup(g);
  joined = want;
  await send("SET_MODE", { match, mode, lang });
}

// Programme cues: ordered by per-match seq; KILL/CLEAR beat a pending delayed TAKE
const latest = new Map<string, { seq: number; action: string }>();
client.on("group-message", (e) => {
  const c = e.message.data as any;       // {cue_id, action, seq, show_at_ms, ttl_ms, preempt, ...}
  if ((latest.get(c.cue_id)?.seq ?? -1) >= c.seq) return;          // duplicate or stale
  latest.set(c.cue_id, { seq: c.seq, action: c.action });
  if (c.action !== "TAKE") return overlay.out(c.cue_id, c.action === "KILL");
  const p = planCue(c.show_at_ms, c.ttl_ms, serverNow(), c.preempt);
  if (p.action === "drop") return console.warn("late_drop", c.cue_id, p.late);
  setTimeout(() => latest.get(c.cue_id)?.action === "TAKE" && overlay.play(c, p.ttlMs), p.inMs);
});
declare const overlay: { play(c: any, ttlMs: number): void; out(id: string, cut: boolean): void };
```

Links: Web PubSub samples https://github.com/Azure/azure-webpubsub · awps-tunnel upstream sample https://github.com/Azure/azure-webpubsub/tree/main/tools/awps-tunnel/server/samples/upstream/ · SPX-GC API routes https://github.com/TuomoKu/SPX-GC/blob/master/routes/routes-api-v1.js · Sofie concepts source https://github.com/Sofie-Automation/sofie-core/blob/main/packages/documentation/docs/user-guide/concepts-and-architecture.md

## Sources

- JSON WebSocket subprotocol `json.webpubsub.azure.v1` — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/reference-json-webpubsub-subprotocol — accessed 20 Oct 2026
- Reliable subprotocol `json.reliable.webpubsub.azure.v1` — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/reference-json-reliable-webpubsub-subprotocol — accessed 20 Oct 2026
- WebSocket client protocols (claims, ackId, Duplicate, permissions) — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/concept-client-protocols — accessed 20 Oct 2026
- Wildcard group role patterns — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/concept-wildcard-group-roles — accessed 20 Oct 2026
- CloudEvents extension for event handler (blocking events, signature, responses) — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/reference-cloud-events — accessed 20 Oct 2026
- How to configure event handler (URL template, auth, validation) — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/howto-develop-eventhandler — accessed 20 Oct 2026
- Generate client access URL (Python token options, Entra data actions) — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/howto-generate-client-access-url — accessed 20 Oct 2026
- OData filter syntax — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/reference-odata-filter — accessed 20 Oct 2026
- Web PubSub client library for JavaScript (invokeEvent preview, recovery 30 s, autoRejoinGroups) — https://learn.microsoft.com/en-us/javascript/api/overview/azure/web-pubsub-client-readme — accessed 20 Oct 2026
- Web PubSub service client library for Python — https://learn.microsoft.com/en-us/python/api/overview/azure/messaging-webpubsubservice-readme — accessed 20 Oct 2026
- Local tunnel tool (preview) — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/howto-web-pubsub-tunnel-tool — accessed 20 Oct 2026
- Socket.IO on Azure overview — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/socketio-overview — accessed 20 Oct 2026
- Unsupported Socket.IO server APIs — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/socketio-supported-server-apis — accessed 20 Oct 2026
- FastAPI WebSockets — https://fastapi.tiangolo.com/advanced/websockets/ — accessed 20 Oct 2026
- Sofie concepts & architecture (Part, Piece, Take, Next, PartInstances) — https://github.com/Sofie-Automation/sofie-core/blob/main/packages/documentation/docs/user-guide/concepts-and-architecture.md — accessed 20 Oct 2026
- Sofie Hold — https://github.com/Sofie-Automation/sofie-core/blob/main/packages/documentation/docs/for-developers/for-blueprint-developers/hold.md — accessed 20 Oct 2026
- Sofie access levels — https://github.com/Sofie-Automation/sofie-core/blob/main/packages/documentation/docs/user-guide/features/access-levels.md — accessed 20 Oct 2026
- CasparCG AMCP protocol (legacy wiki) — https://github.com/CasparCG/help/wiki/AMCP-Protocol — accessed 20 Oct 2026
- SPX-GC repository and `routes/routes-api-v1.js` — https://github.com/TuomoKu/SPX-GC — accessed 20 Oct 2026
- RFC 5905 NTPv4, §8 on-wire protocol — https://www.rfc-editor.org/rfc/rfc5905#section-8 — accessed 20 Oct 2026
- Cristian's algorithm — https://en.wikipedia.org/wiki/Cristian%27s_algorithm — accessed 20 Oct 2026
- MDN `performance.now()` — https://developer.mozilla.org/en-US/docs/Web/API/Performance/now — accessed 20 Oct 2026
- Python `heapq` priority queue notes — https://docs.python.org/3/library/heapq.html — accessed 20 Oct 2026
