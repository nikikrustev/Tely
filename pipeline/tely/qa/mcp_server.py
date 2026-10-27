"""The Stats MCP server: the same 8 Q&A tools over MCP SDK v2 `MCPServer`, streamable HTTP (file 18). OWNER: B (Nikolay).

    pip install -e "pipeline[mcp]"
    python -m tely.qa.mcp_server --port 8080        # POST http://host:8080/mcp

A hosts it in the relay container. MCP is an open protocol (not Microsoft), so any MCP client can use it.

Spoiler firewall (file 43 §2): no tool has a clock argument. The listener's playhead comes from the HTTP header
`X-Tely-Playhead` (seconds since the period start), which A's relay sets from the session. Without a valid header
the server answers as of the START of the cut, the safest choice: nothing has been revealed yet. Every tool is the same
code as tely.qa.call_tool (one implementation of the clamp), so MCP answers equal the relay's answers.
"""
from __future__ import annotations

import argparse
import math
from collections.abc import Mapping
from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field

from . import TOOL_SCHEMAS, tools
from .bundle import Bundle, load_bundle
from .persona import PERSONA

# SEAM(B->A): A's relay sets this header on every MCP request (the model never sees or sets it).
PLAYHEAD_HEADER = "x-tely-playhead"
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
DESCRIPTIONS = {t["name"]: t["description"] for t in TOOL_SCHEMAS}


def playhead_from(headers: Mapping[str, str] | None, bundle: Bundle) -> float:
    """The listener's playhead from the relay's header, clamped to the cut; the cut's start if absent or invalid."""
    raw = None
    if headers:
        raw = next((v for k, v in headers.items() if k.lower() == PLAYHEAD_HEADER), None)
    try:
        p = float(raw) if raw is not None else math.nan
    except (TypeError, ValueError):
        p = math.nan
    return bundle.clamp(p) if math.isfinite(p) else bundle.t0


def build_server(bundle: Bundle | None = None) -> MCPServer:
    b = bundle or load_bundle()
    mcp = MCPServer("tely-qa", title="Tely match tools", version="1.0.0",
                    instructions="Tools for a fan listening to a synthetic football match. " + PERSONA.splitlines()[1])

    def at(ctx: Context) -> float:
        try:
            headers = ctx.headers
        except ValueError:          # no request (in-process call): safest playhead
            headers = None
        return playhead_from(headers, b)

    def run(name: str, args: dict[str, Any], ctx: Context) -> dict[str, Any]:
        return tools.call(name, {k: v for k, v in args.items() if v is not None}, at(ctx), b)

    @mcp.tool(name="get_score_and_clock", description=DESCRIPTIONS["get_score_and_clock"], annotations=READ_ONLY)
    def get_score_and_clock(ctx: Context) -> dict[str, Any]:
        return run("get_score_and_clock", {}, ctx)

    @mcp.tool(name="get_ball_position", description=DESCRIPTIONS["get_ball_position"], annotations=READ_ONLY)
    def get_ball_position(ctx: Context) -> dict[str, Any]:
        return run("get_ball_position", {}, ctx)

    @mcp.tool(name="where_is", description=DESCRIPTIONS["where_is"], annotations=READ_ONLY)
    def where_is(player: Annotated[str, Field(description="Name or shirt number as the fan said it")],
                 ctx: Context) -> dict[str, Any]:
        return run("where_is", {"player": player}, ctx)

    @mcp.tool(name="get_player_stats", description=DESCRIPTIONS["get_player_stats"], annotations=READ_ONLY)
    def get_player_stats(player: str, ctx: Context,
                         metrics: list[Literal["distance_km", "top_speed_kmh", "passes", "shots"]] | None = None
                         ) -> dict[str, Any]:
        return run("get_player_stats", {"player": player, "metrics": metrics}, ctx)

    @mcp.tool(name="get_last_events", description=DESCRIPTIONS["get_last_events"], annotations=READ_ONLY)
    def get_last_events(ctx: Context, n: Annotated[int, Field(ge=1, le=5)] = 3) -> dict[str, Any]:
        return run("get_last_events", {"n": n}, ctx)

    @mcp.tool(name="explain_moment", description=DESCRIPTIONS["explain_moment"], annotations=READ_ONLY)
    def explain_moment(moment_id: str, ctx: Context) -> dict[str, Any]:
        return run("explain_moment", {"moment_id": moment_id}, ctx)

    @mcp.tool(name="what_did_i_miss", description=DESCRIPTIONS["what_did_i_miss"], annotations=READ_ONLY)
    def what_did_i_miss(since: Annotated[str, Field(description="mm:ss")], ctx: Context) -> dict[str, Any]:
        return run("what_did_i_miss", {"since": since}, ctx)

    @mcp.tool(name="set_preferences", description=DESCRIPTIONS["set_preferences"],
              annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True,
                                          open_world_hint=False))
    def set_preferences(ctx: Context,
                        crowd_mix: Annotated[float, Field(ge=0, le=1)] | None = None,
                        haptics: Literal["off", "events", "full"] | None = None,
                        detail: Literal["key", "full"] | None = None) -> dict[str, Any]:
        return run("set_preferences", {"crowd_mix": crowd_mix, "haptics": haptics, "detail": detail}, ctx)

    @mcp.tool(name="adjust_sound", description=DESCRIPTIONS["adjust_sound"],
              annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False,
                                          open_world_hint=False))
    def adjust_sound(sound: Literal["commentator", "crowd", "chants", "reactions", "whistle", "passes", "shots",
                                    "tackles", "saves", "net", "ball_ping"],
                     ctx: Context,
                     change: Annotated[int, Field(ge=-100, le=100)] | None = None,
                     level: Annotated[int, Field(ge=0, le=100)] | None = None) -> dict[str, Any]:
        return run("adjust_sound", {"sound": sound, "change": change, "level": level}, ctx)

    @mcp.tool(name="set_language", description=DESCRIPTIONS["set_language"],
              annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True,
                                          open_world_hint=False))
    def set_language(language: Literal["en", "bg", "es", "ar", "fr", "de", "hi"], ctx: Context) -> dict[str, Any]:
        return run("set_language", {"language": language}, ctx)

    return mcp


def security(allowed_hosts: list[str] | None) -> TransportSecuritySettings | None:
    """DNS-rebinding protection stays on. The SDK default only accepts localhost:*; behind a public host (A's Container
    Apps domain) list it here, e.g. ["as-relay.example.azurecontainerapps.io", "localhost:*"]."""
    if not allowed_hosts:
        return None
    return TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=allowed_hosts,
                                     allowed_origins=[f"https://{h}" for h in allowed_hosts if "*" not in h])


# SEAM(B->A): A can mount this ASGI app inside the relay instead of running a separate process. Run the returned
# server's `session_manager.run()` in the app's lifespan (Starlette mounts do this when you pass lifespan=...).
def http_app(bundle: Bundle | None = None, allowed_hosts: list[str] | None = None):
    """(server, ASGI app) for stateless streamable HTTP at /mcp, JSON responses."""
    srv = build_server(bundle)
    return srv, srv.streamable_http_app(stateless_http=True, json_response=True, transport_security=security(allowed_hosts))


def main() -> None:
    ap = argparse.ArgumentParser(description="Tely Stats MCP server (streamable HTTP).")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--allowed-host", action="append", default=None,
                    help="Host header to accept (repeatable); default: localhost only")
    a = ap.parse_args()
    # File 18: in v2 the transport options go to run(), not MCPServer(...). Stateless: no session state to lose.
    build_server().run(transport="streamable-http", host=a.host, port=a.port, stateless_http=True,
                       transport_security=security(a.allowed_host))


if __name__ == "__main__":
    main()
