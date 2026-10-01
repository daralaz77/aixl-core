# AIXL 0.3 — Deployment (DevOps pass, 2026-10-01)

Scope, stated honestly up front: aixl-core is a small, dependency-free semantic-comparison library with
three ways to reach it — a CLI, an MCP server (stdio, spawned by its host, nothing to deploy), and a
real A2A agent over HTTP (`aixl/agents/a2a_server.py`). **Only the A2A agent is a network service**, so
it is the only thing this document deploys. There is no database, no external API call, no user data
store — "production" here means "a correctly-configured, observable, reliable HTTP process," not a
multi-tier application. Every claim below was built and verified for real on this machine (Docker
Desktop, a real local `kind` Kubernetes cluster) before being written down — see each section's
"Verified" line.

## 1. Architecture

```
GitHub push to main
  │
  ▼
tests workflow (.github/workflows/tests.yml)        — 170+ tests, Python 3.11 & 3.12
  │ (on success)
  ▼
docker-publish workflow (.github/workflows/docker-publish.yml)
  ├─ build the image
  ├─ run it for real, smoke-test a real HTTP round-trip (scripts/smoke_test_a2a.py)
  └─ push ghcr.io/daralaz77/aixl-core:latest + :sha-<short-sha>
  │
  ▼
Deploy target (your choice — both are provided, real, and verified):
  ├─ docker-compose.yml   — single host
  └─ k8s/ (kustomize)     — Deployment (2+ replicas) + Service + HPA + PodDisruptionBudget
                              behind your own Ingress/LoadBalancer, if exposed externally
```

The agent itself: Starlette app (`aixl/agents/a2a_server.py`) = A2A's agent-card + JSON-RPC routes +
three observability routes (`aixl/agents/observability.py`) — `/healthz`, `/readyz`, `/metrics`. No
database, no disk writes at runtime (`InMemoryTaskStore` for the one stateful skill, `aixl_negotiate` —
see BENCHMARK.md §16); every pod is interchangeable, nothing to migrate or back up.

## 2. Deployment flow

1. Push to `main`. CI runs the test suite (Python 3.11 + 3.12).
2. On a green test run, `docker-publish.yml` triggers via `workflow_run`, builds the image, **actually
   runs the built image and drives a real `aixl_compare` call through it** before pushing anything —
   this caught a real bug while building this pipeline (§5).
3. Image lands in `ghcr.io/daralaz77/aixl-core` tagged `latest` and `sha-<short-sha>` (private package,
   matching the repo's own visibility — change that in GHCR's package settings if you want it public).
4. Deploy: `docker compose up -d` for a single host, or `kubectl apply -k k8s/` for a cluster. Neither
   step is automated by CI — this project does not have a real target environment (no domain, no cloud
   account tied to it), so the actual "go live" step is yours to run, deliberately.

## 3. CI/CD pipeline

- **`.github/workflows/tests.yml`** (pre-existing, 2026-09-30): the test gate. Matrix Python 3.11/3.12.
- **`.github/workflows/docker-publish.yml`** (this pass): `workflow_run` off of `tests`, so a red test
  run never produces a published image. Steps: build → **run the real container and call it for real**
  (`scripts/smoke_test_a2a.py`, same script you can run by hand) → only then push, tagged `latest` and
  `sha-<short-sha>` (so a specific commit's image can always be pinned, not just "whatever latest is
  today"). Uses the built-in `GITHUB_TOKEN` — no new secret to create or rotate.
- **Verified**: not just described — see §5 for the real bug this exact build→run→call sequence caught
  before anything shipped.

## 4. Docker / Kubernetes configuration

- **`Dockerfile`**: `python:3.12-slim`, copies only `aixl/` + `data/config.json` (the one file the
  library reads at runtime — not the ~1.4 MB of blind-set/benchmark data under `data/`, which has
  nothing to do with running the agent), runs as a non-root user (uid 10001), `HEALTHCHECK` against
  `/healthz`. **Verified**: built and ran locally; `docker inspect`'s health status reached `healthy`.
- **`docker-compose.yml`**: single-service, maps port 8766, sets `AIXL_A2A_PUBLIC_URL` correctly for
  `localhost` access (see §5 for why this specific variable is not optional), restarts unless stopped.
  **Verified**: `docker compose up -d`, confirmed `/healthz` and a real `aixl_compare` call both work.
- **`k8s/`** (kustomize): `namespace.yaml`, `configmap.yaml` (env vars incl. the in-cluster
  `AIXL_A2A_PUBLIC_URL` default), `deployment.yaml` (2 replicas, `maxUnavailable: 0` rolling update,
  liveness `/healthz` + readiness `/readyz` probes, small CPU/memory requests+limits sized for what
  this process actually needs, non-root + read-only-root-filesystem + all capabilities dropped),
  `service.yaml` (ClusterIP), `hpa.yaml` (CPU-based, 2–10 replicas, needs `metrics-server`),
  `pdb.yaml` (`minAvailable: 1`, so a node drain/upgrade never drops every replica at once).
  **Verified on a real local cluster** (`kind`, not just `kubectl apply --dry-run`): both pods reached
  `Ready` with `readOnlyRootFilesystem: true` (no runtime disk-write crash), a real pod spun up inside
  the cluster called the Service by its real DNS name (`aixl-a2a.aixl.svc.cluster.local`) and got a
  correct `aixl_compare` result back, and — after installing `metrics-server` into the test cluster —
  the HPA reported real CPU usage (`cpu: 4%/70%`), not `<unknown>`.

### Creating the `ghcr-pull-secret` (needed for bug 3 below, and for any real cluster deploy)
`ghcr.io/daralaz77/aixl-core` is a PRIVATE package. `k8s/deployment.yaml` references
`imagePullSecrets: [ghcr-pull-secret]`; create it once per cluster/namespace with a GitHub PAT that has
`read:packages` scope (a fine-grained token scoped to just this, or a classic token with that one
scope — never reuse a broader token here):
```bash
kubectl create secret docker-registry ghcr-pull-secret \
  --namespace aixl \
  --docker-server=ghcr.io \
  --docker-username=<your-github-username> \
  --docker-password=<PAT with read:packages>
```
For `docker-compose.yml` / a plain `docker run` against the published image instead of building
locally: `docker login ghcr.io` once with the same kind of credential before `docker compose pull`.

## 5. Three real bugs found by actually deploying this, not by reading the config

1. **`a2a-sdk[http-server]` does not include an ASGI server.** The first image built cleanly and
   crashed on start: `ModuleNotFoundError: No module named 'uvicorn'`. The CI *test* suite never caught
   this because it also installs `mcp`, and `mcp` happens to depend on `uvicorn` for its own, unrelated
   HTTP transport — a hidden, accidental coupling. Fixed by adding `uvicorn` explicitly to
   `pyproject.toml`'s `a2a` extra, the Dockerfile's `pip install`, and the `tests.yml` install line.
2. **The AgentCard's advertised URL is the URL real clients call back to — not the URL used to fetch
   it.** Running the container with its default `http://127.0.0.1:8766/` and calling it from the host
   via the mapped port (`http://127.0.0.1:18766`) resolved the agent card fine, then failed every real
   JSON-RPC call ("All connection attempts failed") because the SDK's own client reads the ACTUAL
   endpoint from `supportedInterfaces[].url` inside the card, not from whatever URL you used to
   discover it. Fixed by making this configurable (`AIXL_A2A_PUBLIC_URL`) and setting it correctly in
   `docker-compose.yml` (`http://localhost:8766/`) and `k8s/configmap.yaml` (the in-cluster Service DNS
   name) — and documenting, loudly, that exposing this externally (Ingress/LoadBalancer) means
   overriding it again to the real external hostname, or every call will fail the same way.
3. **The published image is private, and nothing could actually pull it.** Found right after the first
   successful publish: `docker pull ghcr.io/daralaz77/aixl-core:latest` failed anonymously
   ("unauthorized"), and even failed with a real personal GitHub token that happened to lack the
   `read:packages` scope (a plain "403 Forbidden", easy to misread as "the publish didn't really work"
   rather than "this credential can't read packages"). `k8s/deployment.yaml` had no `imagePullSecrets`
   at all — anyone actually deploying this manifest as written would hit `ImagePullBackOff`. Fixed by
   adding `imagePullSecrets: [ghcr-pull-secret]` to the Deployment (see above for creating it), and by
   adding a step to `docker-publish.yml` that pulls the just-pushed image fresh (through the real
   registry, with real `GITHUB_TOKEN` auth) and re-runs the smoke test against it — proving the full
   publish → pull cycle actually works, not just that `docker push` returned success.

All three were caught because the artifacts were actually run, called, and pulled — not just built or
written — the lesson this whole project's evidence discipline already applies everywhere else, now
applied to deployment too.

## 6. Monitoring strategy

- **Logs**: `AIXL_LOG_FORMAT=json` (the container default) emits one JSON object per line — timestamp,
  level, logger, message — straight to stdout/stderr, the shape any log aggregator (CloudWatch, Loki,
  Stackdriver, ELK) expects without a custom parser. `AIXL_LOG_FORMAT=text` is available for a readable
  local `python -m aixl.agents.a2a_server` session.
- **Metrics**: `/metrics`, hand-written Prometheus text exposition format (no new dependency — this
  project has exactly 7 counters to track: total requests, compares, negotiations started/paused/
  completed/rejected, errors). Any Prometheus-compatible scraper reads it with zero extra config.
- **Health**: `/healthz` (liveness — is the process up) and `/readyz` (readiness — distinct on purpose,
  so a future dependency this agent doesn't have today has somewhere to report without a wire-format
  change for every caller) back the Docker `HEALTHCHECK` and the Kubernetes probes directly.
- **What this does NOT include**: no distributed tracing, no alerting rules, no dashboards — genuinely
  not needed yet for a single stateless comparison endpoint with no production traffic; add them when
  there is a real operational reason to, not speculatively.

## 7. Production deployment checklist

- [ ] CI green on `main` (`tests` workflow) for the commit you intend to ship.
- [ ] `docker-publish` workflow succeeded — a new image is in `ghcr.io/daralaz77/aixl-core`, tagged
      with that commit's short SHA (prefer pinning to the SHA tag over `latest` for anything you
      actually care about rolling back cleanly).
- [ ] **Set `AIXL_A2A_PUBLIC_URL` to the real externally-reachable address** before exposing this
      anywhere beyond a single host or cluster-internal callers (§5, bug 2) — this is the single most
      likely real misconfiguration, because everything else (health checks, agent-card fetch) looks
      fine even when this is wrong.
- [ ] If exposing externally: a real Ingress/LoadBalancer with TLS in front of the Service (this repo
      does not include one — it depends on your ingress controller and domain, neither of which this
      project has).
- [ ] `metrics-server` installed in the target cluster if you want the HPA to actually scale (most
      managed clusters — EKS/GKE/AKS — already have it; `kind`/bare `minikube` do not by default).
- [ ] **`ghcr-pull-secret` created in the target namespace** (§4) — without it, every pod gets
      `ImagePullBackOff` against this private package (§5, bug 3); a health check never even starts,
      so this fails loudly and immediately, unlike bug 2's silent-until-a-real-call failure mode.
- [ ] Point your log aggregator and metrics scraper at stdout/stderr and `/metrics` respectively.
- [ ] Decide the GHCR package's visibility (private, matching the repo, by default) — make it public
      only if you actually want anyone to be able to `docker pull` it.
- [ ] After deploying: `curl <public-url>/healthz` AND a real `aixl_compare` call (e.g.
      `python scripts/smoke_test_a2a.py <public-url>`) — the health check passing is not sufficient
      proof the deployment actually works (§5, bug 2 passed every health check and still failed every
      real call).
