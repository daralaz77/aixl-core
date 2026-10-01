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
  project has exactly 8 counters to track: total requests, compares, negotiations started/paused/
  completed/rejected/expired, errors). Any Prometheus-compatible scraper reads it with zero extra
  config. `aixl_negotiate_expired_total` (§9) is worth actually watching: a sustained climb means
  either real abandoned negotiations (a human never answered) or a client-side bug that starts
  negotiations and never resumes them — the TTL sweep hides the memory-growth symptom, not the cause.
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
- [ ] **`ghcr-pull-secret` created in the target namespace** (§4) — without it, every pod gets
      `ImagePullBackOff` against this private package (§5, bug 3); a health check never even starts,
      so this fails loudly and immediately, unlike bug 2's silent-until-a-real-call failure mode.
- [ ] **Do not raise `k8s/deployment.yaml`'s `replicas` above 1** (and do not re-enable `hpa.yaml`)
      until a shared TaskStore exists (§8) — confirmed for real that >1 replica breaks
      `aixl_negotiate`'s resume ~60% of the time, silently (every health check still passes).
- [ ] Point your log aggregator and metrics scraper at stdout/stderr and `/metrics` respectively.
- [ ] Decide the GHCR package's visibility (private, matching the repo, by default) — make it public
      only if you actually want anyone to be able to `docker pull` it.
- [ ] After deploying: `curl <public-url>/healthz` AND a real `aixl_compare` call (e.g.
      `python scripts/smoke_test_a2a.py <public-url>`) — the health check passing is not sufficient
      proof the deployment actually works (§5, bug 2 passed every health check and still failed every
      real call).
- [ ] **If you ever need `aixl_negotiate` to survive >1 replica or a pod restart**: read §8 first —
      a real multi-turn negotiation was confirmed to be silently lost on a pod restart even with
      session affinity, and that's a real, deliberate limitation, not an oversight to patch over.
- [ ] Watch `aixl_negotiate_expired_total` (§9) if you care about how many negotiations are actually
      being abandoned vs. completed — the default 1-hour TTL (`AIXL_TASK_TTL_SECONDS`) bounds memory
      either way, but a high rate is still worth knowing about.
- [ ] If raising `k8s/deployment.yaml`'s CPU limit, re-measure before assuming `/healthz` stays
      responsive under a concurrent burst — `AIXL_MAX_CONCURRENT_CPU_WORK` (default 4, §10) was tuned
      against the current 500m limit specifically, not a universal safe number.

## 8. Critical reading: the "reliability" deployment broke the one stateful feature

Found by continuing to test after the first 3 bugs were fixed, not by inspection: **the original
`replicas: 2` Deployment — written specifically "for reliability" — silently broke `aixl_negotiate`'s
multi-turn pause/resume most of the time.** `aixl/agents/a2a_negotiate.py`'s paused-task state lives in
`InMemoryTaskStore`, which is per-process. A plain `ClusterIP` Service load-balances each new connection
across pods with no awareness of which pod is holding which paused task.

**Measured, not assumed**: a real 2-replica `kind` deployment, 20 independent negotiate-then-resume
cycles (a fresh client/connection for the resume, simulating the realistic case of a human answering
later from a separate request) — **12 of 20 resumes failed with `TaskNotFoundError`**. Every health
check, readiness probe, and agent-card fetch passed the whole time; nothing about the deployment looked
broken from the outside. Adding `sessionAffinity: ClientIP` to the Service brought 20/20 cycles back to
passing — but then a real pod restart (simulating a rolling update or node reschedule) while a task was
paused made the very next resume fail 100% of the time (`TaskNotFoundError`, confirmed with a real
`kubectl delete pod`), because affinity only matters for routing a request to a *pod that still exists*.

**The fix applied today**: `k8s/deployment.yaml` runs **`replicas: 1`** (strategy `Recreate`, not
`RollingUpdate`, so a deploy never briefly runs 2 pods) — correctness over redundancy, honestly, for a
feature with zero production traffic today. `hpa.yaml` and `pdb.yaml` are kept in the repo but excluded
from `kustomization.yaml`, each commented with why: an HPA scaling past 1 reintroduces the exact bug;
a PDB with `minAvailable: 1` at `replicas: 1` would block every voluntary node drain forever. Session
affinity stays on the Service as a harmless, if incomplete, safety net.

**What this trades away**: `aixl_compare` (fully stateless) now also runs at 1 replica — a pod crash
means a brief restart gap (seconds, k8s's own restart policy) rather than true zero-downtime redundancy.
Judged an acceptable, disclosed trade-off for an experimental agent with no real traffic yet, not a
permanent architectural ceiling.

**The real path to restore both correctness AND horizontal scaling** (not built today — this is a new
infrastructure dependency decision, not something to add unilaterally for a feature that doesn't have
real traffic yet):

1. **A shared `TaskStore`** — `a2a-sdk` already ships `DatabaseTaskStore` (SQLAlchemy-backed). SQLite on
   a shared volume is the *wrong* choice here (SQLite does not handle concurrent writers from multiple
   pods/nodes safely); a real Postgres (or MySQL) instance is the correct backing store. This is the
   SDK's own intended answer, and the most "normal" fix — at the cost of a new stateful dependency this
   project has deliberately avoided everywhere else.
2. **Split the agent into two Deployments** behind path/skill-based routing: `aixl_compare` (stateless,
   scale freely, no changes needed) and `aixl_negotiate` (kept at `replicas: 1`, or backed by option 1
   if it ever needs to scale too). More architecturally correct long-term, more work today (routing,
   two images or one image with a mode flag, two Services).
3. **Stay at `replicas: 1` indefinitely** if real traffic never materializes — the honest "do nothing
   further" option, valid as long as it stays true.

No recommendation is made between these three here — unlike the `A2AAdapter`/negotiation design choices
earlier in this project, this one trades off a real new dependency (a database) against real
architectural effort (splitting the deployment), and should be picked when there is an actual traffic
or reliability number driving the decision, not speculatively.

## 9. A second critical finding: abandoned negotiations grew memory without bound

Asked again "what's still missing" after §8 shipped, and found this by load-testing the fix rather than
re-reading the config. `a2a-sdk`'s `InMemoryTaskStore` has no eviction at all — every `aixl_negotiate`
task it ever saves stays in memory forever, including one that pauses (`TASK_STATE_INPUT_REQUIRED`)
waiting for a human and is simply never resumed.

**Measured, not assumed**: started and abandoned 200 real `aixl_negotiate` tasks against a running
container — memory climbed from ~60MB to ~71MB, with nothing to bring it back down. At the `k8s/`
Deployment's 256Mi limit, a few thousand abandoned negotiations (an idle client that starts but never
answers, a buggy integration, or deliberate abuse against a reachable endpoint) would OOMKill the pod —
a real, unbounded resource-exhaustion risk, not a hypothetical one.

**Fixed**: `aixl/agents/expiring_task_store.py`'s `ExpiringTaskStore` wraps `InMemoryTaskStore` and
deletes a task once it has gone untouched for longer than `AIXL_TASK_TTL_SECONDS` (default 3600 —
1 hour, long enough for a real human to actually read and answer a paused CLARIFY question; short
enough to bound growth). The sweep runs as a side effect of every `save()` — no separate background
timer needed at this scale — and increments a new `aixl_negotiate_expired_total` counter so a sustained
climb is visible in `/metrics` rather than silent.

**Verified**: `tests/test_expiring_task_store.py` (4 fast unit tests, no Docker needed) proves a task
within its TTL survives and a stale one is swept without disturbing an unrelated fresh one. Re-ran the
exact 200-abandoned-task scenario against a real container with a short TTL (3s): memory stayed at
~52MB instead of climbing, `aixl_negotiate_expired_total` correctly counted all 202 sweeps, and a task
resumed well within the TTL window still converged correctly — the fix bounds growth without breaking
the feature it's protecting.

**Also fixed in the same pass**: `scripts/smoke_test_a2a.py` (used by `docker-publish.yml` before every
publish) only ever checked `aixl_compare` — a real regression in `aixl_negotiate` could have shipped
without the pipeline noticing. It now checks both skills (the ordinary, single-call auto-resolve path
for negotiate; a CI smoke test runs unattended, so the human-pause flow isn't exercised there — that's
what `tests/test_a2a_integration.py`'s own pause/resume tests are for).

## 10. A third critical finding: CPU-bound work blocked health checks under concurrent load — and a measurement lesson along the way

Looked for more gaps again (user: "otra vuelta") and suspected `aixl.compare()`/`_advance()` — synchronous, regex-heavy, CPU-bound code called directly inside `async def execute()` — might block the single asyncio event loop under concurrent load, including the `/healthz` request a liveness probe depends on.

**First measurement, and a real methodology mistake caught before trusting it**: fired 900 concurrent `aixl_compare` calls at a 1-CPU container while polling `/healthz` *from the same Python asyncio process*. Max `/healthz` latency: 4.5s — past the Deployment's 3s liveness timeout. Before accepting that number, re-ran it with the load generator and the `/healthz` poller as **two genuinely separate OS processes** (a background Python load-generator, `/healthz` polled by a plain `curl` loop) — the number dropped to ~1s, revealing that a meaningful part of the first measurement was the *test harness's own event loop* contending with itself, not the server. Repeating the clean, separate-process measurement 3 times against the **original** (unfixed) code still showed a real, reproducible problem, just smaller than first thought: **2.45s, 2.48s, 3.27s** — one of three trials genuinely exceeded the 3s liveness timeout.

**Fixed**: `aixl/agents/concurrency.py`'s `run_cpu_bound()` wraps `aixl.compare()` (in `a2a_server.py`) and `_compute_start()`/`_advance()` (in `a2a_negotiate.py`) with `asyncio.to_thread` *plus* a small semaphore (`AIXL_MAX_CONCURRENT_CPU_WORK`, default 4). `asyncio.to_thread` alone was tried first and was **not enough** — re-running the exact same 900-request burst after that change alone still showed a 4.2s spike, because Python's default `ThreadPoolExecutor` happily spins up ~32 workers that all contend for the GIL and the container's real (1-core) CPU budget just as badly as before. The semaphore is what actually fixed it: bounding how many calls run at once means the rest `await` cheaply in the event loop (no competing OS thread, no GIL contention) instead of piling onto an oversubscribed thread pool.

**Re-verified with the same honest, separate-process methodology, 3 clean trials against the fixed code**: **0.54s, 0.86s, 0.77s** — comfortably under the timeout every time, a real and consistent improvement over the original's 2.45–3.27s spread, not just a different single lucky number.

Honest scope: this was tested at 900 concurrent requests on a constrained 1-CPU container — a stand-in for "a burst bigger than the box can handle," not a specific real traffic number (there is none yet). `AIXL_MAX_CONCURRENT_CPU_WORK=4` is a starting default matched loosely to `k8s/deployment.yaml`'s own `resources.limits.cpu: "500m"`; raise it if the Deployment's CPU limit is raised, and re-measure rather than assume a bigger number is strictly better (too high defeats the point; too low adds needless queuing latency under legitimate concurrent load). No rate limiting was added at the request-admission level (a 429-style reject beyond some concurrency) — the semaphore provides backpressure by making excess callers wait, which was sufficient to fix the measured problem; an explicit reject-based limiter remains a reasonable future addition if real abuse, not just a synthetic burst, is ever observed.
