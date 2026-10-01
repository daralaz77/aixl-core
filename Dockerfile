# syntax=docker/dockerfile:1
# Packages ONLY the A2A agent (aixl/agents/a2a_server.py) — the one network-facing component of this
# project. The rest (cli.py, lab/, benchmarks/, tests/) is dev/research tooling that has no business
# running in a container; aixl-core itself is never pip-installed (see .github/workflows/tests.yml's
# own comment: this repo's multi-top-level-dir layout defeats setuptools auto-discovery), so this
# image copies the package tree directly and runs it via PYTHONPATH, same as CI and local dev do.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    AIXL_A2A_HOST=0.0.0.0 \
    AIXL_LOG_FORMAT=json \
    PORT=8766

# Runtime dependency only (starlette + the official a2a-sdk + uvicorn as the ASGI server) —
# mcp/pytest/tiktoken are dev-only. uvicorn is listed explicitly: a2a-sdk[http-server] only pulls in
# starlette/sse-starlette, NOT an ASGI server — found the hard way by actually running this image the
# first time (it crashed with ModuleNotFoundError: uvicorn). CI's test suite never caught this because
# it installs `mcp` alongside a2a-sdk, and `mcp` itself happens to depend on uvicorn for its own
# (unrelated, HTTP-transport) use — a real, fragile hidden coupling, not a real fix, now made explicit
# here and in pyproject.toml's own `a2a` extra.
RUN pip install --no-cache-dir "a2a-sdk[http-server]" uvicorn

# Only what the agent actually imports at runtime: the aixl/ package and its one config file
# (aixl/core/ontology.py's load_config() resolves data/config.json relative to the package, so this
# sibling layout must be preserved) — not the 1.4MB of blind-set/benchmark data under data/ that has
# nothing to do with running the agent.
COPY aixl/ ./aixl/
COPY data/config.json ./data/config.json

RUN useradd --no-create-home --uid 10001 aixl && chown -R aixl:aixl /app
USER aixl

EXPOSE 8766

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT','8766') + '/healthz', timeout=2)"

CMD ["python", "-m", "aixl.agents.a2a_server"]
