# Third-party software

The core library (`aixl/`, the semantic comparator, the CLI) has **no runtime dependency**: `pyproject.toml` declares `dependencies = []`. Everything below is an **optional extra** or a development tool, installed only when you ask for it. The machine-readable list is the SBOM (`python scripts/make_sbom.py`, CycloneDX 1.5; CI publishes it as the `sbom` artifact of every run).

| Package | Extra | Used for | Where | Notes |
|---|---|---|---|---|
| `mcp` | `mcp` | MCP server (`aixl/mcp_server.py`) | tools exposed over stdio | pulls `uvicorn` / `httpx` transitively |
| `a2a-sdk[http-server]` | `a2a` | A2A agent (`aixl/agents/a2a_server.py`) | network-facing, token required off loopback | needs an ASGI server |
| `uvicorn` | `a2a` | ASGI server for the A2A agent | network-facing | listed explicitly, see the comment in `.github/workflows/tests.yml` |
| `httpx` | `llm` | LLM translator and arbiter judges | outbound calls to the providers you configure | your texts go to those providers |
| `cryptography` | `signing` | Ed25519 signed envelope (`aixl/signed_envelope.py`) | local | no external security review of our use of it (LIMITATIONS.md E-SIGNED-ENVELOPE) |
| `opentelemetry-api` | `otel` | optional tracing | local | |
| `pytest`, `tiktoken` | `dev` | tests, token counts | development only | never shipped in the image |

Container base image: see `Dockerfile` (runs as a non-root user).

## Access privileges (who can do what)
- Repository `daralaz77/aixl-core` (public): one maintainer with admin rights. No other collaborator. Direct push to `main` is allowed; force-push and branch deletion on `main` are blocked.
- GitHub Actions: workflows run with `contents: read` unless a job needs more (`security-events: write` for CodeQL and Scorecard, `packages: write` for the image publish).
- Container registry: `ghcr.io/daralaz77/aixl-core`, written only by the `docker-publish` workflow after the tests and the 401 smoke test pass.
- Secrets: none are stored in the repository; secret scanning and push protection are enabled.

## How this is kept up to date
- Dependabot opens weekly pull requests for GitHub Actions, pip and Docker (`.github/dependabot.yml`) and security updates are enabled.
- CodeQL (Python) runs on every push, pull request and weekly; OpenSSF Scorecard runs on every push and weekly.
- Subscribe, as maintainer: GitHub security advisories for the packages above and the Python release announcements. This is a manual habit, not automation.
