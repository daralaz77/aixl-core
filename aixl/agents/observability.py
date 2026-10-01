"""Health, readiness and metrics for aixl/agents/a2a_server.py (DevOps/production-readiness pass,
2026-10-01). Hand-rolled, no new dependency: a Prometheus client library would be the "normal" choice,
but this agent is a single small process with a handful of counters, so a few global ints and a plain
Prometheus TEXT-format response (the exposition format itself needs no client library, any scraper that
speaks Prometheus can read it) cover the real need without pulling in a dependency this project doesn't
otherwise have. See DEPLOYMENT.md for how `/healthz`/`/readyz`/`/metrics` are used by Docker/Kubernetes."""
import json
import logging
import os
import time

from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

_START_TIME = time.time()


class _JSONLogFormatter(logging.Formatter):
    """One JSON object per line: timestamp, level, logger name, message — the shape any log
    aggregator (CloudWatch, Loki, Stackdriver, ELK) expects to parse without a custom grok pattern."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> None:
    """Called once at process start (main()). AIXL_LOG_FORMAT=json (the default — this agent is meant
    to run in a container) switches every handler on the root logger to one JSON line per record;
    AIXL_LOG_FORMAT=text keeps plain text, friendlier for an interactive local `python -m
    aixl.agents.a2a_server` session. AIXL_LOG_LEVEL sets the level (default INFO)."""
    level = os.environ.get("AIXL_LOG_LEVEL", "INFO").upper()
    fmt = os.environ.get("AIXL_LOG_FORMAT", "json").lower()
    handler = logging.StreamHandler()
    handler.setFormatter(_JSONLogFormatter() if fmt == "json" else
                          logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

_counters = {
    "aixl_requests_total": 0,
    "aixl_compare_total": 0,
    "aixl_negotiate_started_total": 0,
    "aixl_negotiate_paused_total": 0,
    "aixl_negotiate_completed_total": 0,
    "aixl_negotiate_rejected_total": 0,
    "aixl_negotiate_expired_total": 0,
    "aixl_errors_total": 0,
}


def inc(name: str, by: int = 1) -> None:
    _counters[name] = _counters.get(name, 0) + by


async def healthz(request: Request) -> JSONResponse:
    """Liveness: the process is up and able to handle a request. Never checks dependencies — this
    agent has none (no database, no external service) — so liveness here only ever reflects whether
    the event loop itself is responsive."""
    return JSONResponse({"status": "ok", "uptime_seconds": round(time.time() - _START_TIME, 1)})


async def readyz(request: Request) -> JSONResponse:
    """Readiness: distinct from liveness so a rolling deploy / autoscale can hold traffic back from a
    pod that is up but not yet ready. Identical to healthz today since this agent has no startup
    dependency to wait on — kept as its own endpoint/route so a future one (e.g. a real task store
    needing a connection) has somewhere to report without a wire-format change for every caller."""
    return JSONResponse({"status": "ready"})


async def metrics(request: Request) -> PlainTextResponse:
    """Prometheus text exposition format (https://prometheus.io/docs/instrumenting/exposition_formats/),
    hand-written: `# HELP`/`# TYPE` plus one `name value` line per counter. Any Prometheus-compatible
    scraper (Prometheus itself, Grafana Agent, VictoriaMetrics, Datadog's OpenMetrics check, ...) can
    read this with zero extra configuration beyond pointing it at this path."""
    lines = [f"aixl_uptime_seconds {time.time() - _START_TIME:.1f}"]
    for name, value in _counters.items():
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {value}")
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


def observability_routes() -> list[Route]:
    return [
        Route("/healthz", healthz, methods=["GET"]),
        Route("/readyz", readyz, methods=["GET"]),
        Route("/metrics", metrics, methods=["GET"]),
    ]
