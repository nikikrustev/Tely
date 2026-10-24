"""Custom events from the relay to Application Insights (D19). OWNER: A (potencialbg).

Same OpenTelemetry route as the Director's traces (pipeline/audiostands/agents/tracing.py, D16): the Azure Monitor
distro, configure_azure_monitor(), and the connection string from APPLICATIONINSIGHTS_CONNECTION_STRING (a Container
Apps secret, infra/relay.bicep). It is never printed or logged. Only one Python logger is exported, and a log record
with "microsoft.custom_event.name" becomes a row in the customEvents table. Tracing, metrics, live metrics and
auto-instrumentation stay off, so the relay sends nothing else (no request spans, no IPs).

Without the package (CI, requirements-test.txt) or the string (local runs), events go to stdout as one JSON line,
which Container Apps also keeps in Log Analytics, so an answer is never silently dropped.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
from typing import Callable

CONN = "APPLICATIONINSIGHTS_CONNECTION_STRING"
LOGGER = "audiostands.relay.events"
SERVICE = "audiostands-relay"
Tracker = Callable[[str, dict[str, str]], None]


def _stdout(name: str, props: dict[str, str]) -> None:
    print(json.dumps({"event": name, **props}, ensure_ascii=False), flush=True)


def make_tracker(env: dict[str, str] | None = None) -> tuple[Tracker, str]:
    """(track, where): where is "app_insights" or "stdout (<why>)"."""
    e = os.environ if env is None else env
    conn = (e.get(CONN) or "").strip()
    if not conn:
        return _stdout, f"stdout ({CONN} not set)"
    if importlib.util.find_spec("azure.monitor.opentelemetry") is None:
        return _stdout, "stdout (azure-monitor-opentelemetry not installed)"
    # The distro reads these to switch its trace and metric pipelines off; logs stay on.
    os.environ.setdefault("OTEL_TRACES_EXPORTER", "none")
    os.environ.setdefault("OTEL_METRICS_EXPORTER", "none")
    from azure.monitor.opentelemetry import configure_azure_monitor
    from opentelemetry.sdk.resources import Resource

    off = {"enabled": False}
    configure_azure_monitor(
        connection_string=conn, logger_name=LOGGER, resource=Resource.create({"service.name": SERVICE}),
        enable_live_metrics=False, enable_performance_counters=False,
        instrumentation_options={lib: off for lib in ("azure_sdk", "django", "fastapi", "flask", "psycopg2",
                                                      "requests", "urllib", "urllib3")})
    # azure-core logs every exporter request and response at INFO ("Request URL ... Transmission succeeded"), which
    # flooded the console logs on the first deploy (24 Oct). Warnings and errors still show.
    logging.getLogger("azure").setLevel(logging.WARNING)
    log = logging.getLogger(LOGGER)
    log.setLevel(logging.INFO)
    log.propagate = False

    def track(name: str, props: dict[str, str]) -> None:
        log.info(name, extra={"microsoft.custom_event.name": name, **props})

    return track, "app_insights"
