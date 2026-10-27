"""OpenTelemetry for the Director workflow -> Application Insights (file 18 §5).

configure_azure_monitor(...) then enable_instrumentation(), as file 18 says. The connection string comes from the
process env, else from the azd env ("judge"), where `azd provision` stores the Bicep output. It is never printed,
logged or written to a tracked file. Off (and silent) whenever azure-monitor-opentelemetry or the string is missing.
Prompt and reply text are not captured (Agent Framework's ENABLE_SENSITIVE_DATA stays off).
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess

CONN = "APPLICATIONINSIGHTS_CONNECTION_STRING"
SERVICE = "tely-director"


def connection_string(env: dict[str, str], azd_env: str = "judge") -> str | None:
    if os.environ.get(CONN) or env.get(CONN):
        return os.environ.get(CONN) or env.get(CONN)
    azd = shutil.which("azd")
    if azd is None:
        return None
    try:
        out = subprocess.run([azd, "env", "get-value", CONN, "-e", azd_env], capture_output=True, text=True,
                             timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    value = out.stdout.strip()
    return value if out.returncode == 0 and value.startswith("InstrumentationKey=") else None


def setup(env: dict[str, str]) -> str:
    """Returns where traces go: "app_insights" or "off (<why>)"."""
    if importlib.util.find_spec("azure.monitor.opentelemetry") is None:
        return "off (azure-monitor-opentelemetry not installed)"
    conn = connection_string(env)
    if not conn:
        return f"off ({CONN} not in the env or the azd env; run azd provision)"
    from agent_framework.observability import create_resource, enable_instrumentation
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(connection_string=conn, resource=create_resource(service_name=SERVICE))
    enable_instrumentation(enable_sensitive_data=False)
    return "app_insights"


def flush() -> None:
    """Export buffered spans before the process exits (the batch exporter would otherwise drop the tail)."""
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        if hasattr(provider, "force_flush"):
            provider.force_flush(timeout_millis=15_000)
    except ImportError:
        pass
