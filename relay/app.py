"""The relay: live spoken questions (Voice Live) and B's Stats MCP server, in one container. OWNER: A (potencialbg).

    uvicorn relay.app:app --port 8080        # from the repo root, PYTHONPATH=pipeline;.  (see relay/README.md)

Routes:
- GET  /health   liveness and the current DEMO_MODE. The page calls it on load to wake a scaled-to-zero replica (D6).
- WS   /voice    one fan's live Ask (voicelive.Bridge). Text frames are JSON control messages, binary frames are
                 PCM16 24 kHz mono audio (mic up, answer down).
- POST /mcp      B's audiostands.qa.mcp_server, streamable HTTP, stateless (file 18). The listener's playhead comes from
                 the X-AudioStands-Playhead header; without it the tools answer as of the start of the cut.
No keys anywhere: Voice Live uses the container's managed identity (file 30), and the browser never sees a token.
"""
from __future__ import annotations

import asyncio
import collections
import contextlib
import json
import os
import time
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from audiostands.qa.bundle import Bundle, load_bundle

from .caps import Caps
from .clips import refusal
from .voicelive import Bridge, Link, connect_voice_live, log_line

CONNECT_TIMEOUT_S = 8.0     # the browser falls back to presets after 8 s anyway (BUILD_PLAN Stage 7)
MCP_CALLS_PER_MIN = 60      # ours; MCP spec: servers "MUST ... rate limit tool invocations" (file 40 §3)


def _csv(name: str, default: str = "") -> list[str]:
    return [s.strip() for s in os.environ.get(name, default).split(",") if s.strip()]


def client_ip(headers: Any, peer: Any) -> str:
    xff = headers.get("x-forwarded-for", "")          # set by the Container Apps ingress (file 21, unverified)
    return xff.split(",")[0].strip() or (peer.host if peer else "?")


def create_app(*, bundle: Bundle | None = None, caps: Caps | None = None,
               connect: Callable[[], Awaitable[Link]] = connect_voice_live, mount_mcp: bool = True) -> FastAPI:
    b = bundle or load_bundle()
    c = caps or Caps()
    origins = _csv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    mcp_srv = None
    mcp_app = None
    if mount_mcp:
        # SEAM(A->B): B's MCP server, hosted here (TEAM_SPLIT.md "Relay"). B's http_app() keeps DNS-rebinding protection
        # on; MCP_ALLOWED_HOSTS lists our public host name (set by infra/relay.bicep).
        from audiostands.qa.mcp_server import http_app
        mcp_srv, mcp_app = http_app(b, _csv("MCP_ALLOWED_HOSTS", "localhost:*,127.0.0.1:*"))

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI):
        # A mounted Starlette app's own lifespan doesn't run, so the MCP session manager starts here (B's http_app note).
        if mcp_srv is not None:
            async with mcp_srv.session_manager.run():
                yield
        else:
            yield

    app = FastAPI(title="Audio Stands relay", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=[])
    app.state.caps, app.state.bundle = c, b
    mcp_hits: dict[str, collections.deque] = collections.defaultdict(collections.deque)

    @app.middleware("http")
    async def limit_mcp(req: Request, call_next):
        if req.url.path.startswith("/mcp"):
            ip, now = client_ip(req.headers, req.client), time.time()
            q = mcp_hits[ip]
            while q and q[0] <= now - 60:
                q.popleft()
            if len(q) >= MCP_CALLS_PER_MIN:
                return JSONResponse({"error": "rate_limit"}, status_code=429, headers={"Retry-After": "60"})
            q.append(now)
        return await call_next(req)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "mode": c.mode()}

    @app.websocket("/voice")
    async def voice(ws: WebSocket) -> None:
        origin = ws.headers.get("origin", "")
        if origins and origin and origin not in origins:
            await ws.close(code=1008)            # only our own pages may open a paid Voice Live session
            return
        await ws.accept()
        ip = client_ip(ws.headers, ws.client)
        if (reason := c.open_session(ip)) is not None:
            await ws.send_json(refusal(reason))
            await ws.close()
            return
        bridge: Bridge | None = None
        pump: asyncio.Task | None = None
        try:
            try:
                link = await asyncio.wait_for(connect(), CONNECT_TIMEOUT_S)
            except Exception as exc:              # no Voice Live: the page says so and opens the presets
                log_line(json.dumps({"voice_live_connect_failed": type(exc).__name__}))
                await ws.send_json(refusal("unavailable"))
                await ws.close()
                return
            lock = asyncio.Lock()               # the pump and this loop both send; one frame at a time

            async def send_json(o: dict[str, Any]) -> None:
                async with lock:
                    await ws.send_json(o)

            async def send_bytes(data: bytes) -> None:
                async with lock:
                    await ws.send_bytes(data)

            bridge = Bridge(link, bundle=b, caps=c, to_client=send_json, to_client_audio=send_bytes, connect=connect)
            await bridge.start()
            pump = asyncio.create_task(bridge.pump())
            await send_json({"type": "ready"})
            while True:
                try:
                    msg = await asyncio.wait_for(ws.receive(), c.idle_s)
                except asyncio.TimeoutError:
                    await send_json({"type": "closed", "reason": "idle"})   # file 40 §6: close after 90 s idle
                    break
                if msg.get("type") == "websocket.disconnect":
                    break
                if msg.get("bytes") is not None:
                    await bridge.audio(msg["bytes"])
                    continue
                try:
                    m = json.loads(msg.get("text") or "{}")
                except json.JSONDecodeError:
                    continue
                kind = m.get("type")
                if kind == "ask":
                    await bridge.ask(m.get("playhead_s"))
                elif kind == "commit":
                    await bridge.commit()
                elif kind == "cancel":
                    await bridge.cancel()
                elif kind == "metrics":
                    bridge.metrics(m.get("client_latency_ms"))
        except WebSocketDisconnect:
            pass
        finally:
            c.close_session(ip)
            if bridge is not None:
                await bridge.close()
            if pump is not None:
                pump.cancel()
            with contextlib.suppress(Exception):
                await ws.close()

    if mcp_app is not None:
        app.mount("/", mcp_app)                  # last: B's app serves /mcp, anything else is 404
    return app


def __getattr__(name: str) -> Any:
    # `uvicorn relay.app:app` builds the real app on first access, so importing this module in tests loads nothing.
    if name == "app":
        globals()["app"] = create_app()
        return globals()["app"]
    raise AttributeError(name)
