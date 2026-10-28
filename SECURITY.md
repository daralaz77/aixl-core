# Security policy

AIXL is maintained by one person. This policy says what to expect, so that nobody waits for something that will not come.

## Reporting a vulnerability
Email **director@daralaz.com** with the subject `AIXL security`. Please include: what you found, how to reproduce it (the smallest input or request that shows it), the version or commit, and what you think the impact is.
**Please do not open a public issue or post it in a forum before we have talked.** There is no PGP key; if the report is sensitive, say so in the first line and keep the details for a reply.

What you can expect, as a single maintainer's best effort and not a service level:
| Step | Target |
|---|---|
| Acknowledgement | within 5 working days |
| First assessment (is it real, how severe) | within 15 working days |
| Fix or mitigation for a confirmed high or critical issue | as fast as possible; we will tell you the plan within that assessment |
| Public disclosure | coordinated with you, normally after a fix is available and in any case not later than 90 days after the report |
There is no bug bounty. We will credit you in the release notes if you wish.

## Supported versions
Only the latest commit on `main` and the latest published image (`ghcr.io/daralaz77/aixl-core:latest`) are supported. Version 0.5.x is experimental and has no long-term-support branch.

## What is in scope
- The **A2A agent** (`aixl/agents/a2a_server.py`, `aixl/agents/guard.py`): authentication bypass, rate-limit or size-cap bypass, denial of service, request smuggling, information disclosure.
- The **MCP server** (`aixl/mcp_server.py`) and its tools.
- The **integrity envelope** (`aixl/envelope.py`): a way to make `verify` return `MATCH` for a text whose critical slots changed.
- The **verified comparison** (`aixl.compare_verified`) and `aixl.relay_check`: an input that makes them report EQUIVALENT or `ok: true` for a meaning change they claim to detect is a **security-relevant bug** for this project (examples fixed so far: a Portuguese `dos` read as the number 2; an `and`→`or` flip).
- The **container image** and the deployment files (`Dockerfile`, `k8s/`, `docker-compose.yml`).
- The arbiter's audit layer (`aixl/arbiter.py`): ways to make a stored decision be reused for different texts, or to turn a judge's invalid answer into SAME.

Out of scope: vulnerabilities in third-party software (report them to its maintainers; tell us if our usage makes it worse), social engineering, attacks that need the deployer's token or a machine that is already compromised, and the accuracy limits already documented in `LIMITATIONS.md` (the lexicon is closed, the detector is not an equivalence prover).

## What the code does to protect a deployment
These are facts about the current code, each covered by tests; they are not a guarantee.
- The A2A agent **refuses to start on a non-loopback address without `AIXL_A2A_TOKEN`** (unless `AIXL_A2A_ALLOW_ANONYMOUS=1` is set on purpose). With a token, every request except `/healthz`, `/readyz` and the agent card needs `Authorization: Bearer <token>`; the comparison is constant-time.
- Per-client **rate limit** (`AIXL_A2A_RATE_PER_MIN`, default 120) and **request-body cap** (`AIXL_A2A_MAX_BODY_BYTES`, default 262 144 bytes).
- **Analysis input cap** (`AIXL_MAX_INPUT_CHARS`, default 16 384 characters): larger inputs are refused instead of analysed.
- The core library has **no runtime dependencies**, never executes the text it analyses and performs no action on behalf of a message. The only process it starts is the sender agent of the MCP tool `aixl_negotiate_autonomous`: a fixed command (`python -m aixl.agents.sender_agent --text <text>`) launched as an argument list, never through a shell, with an explicit minimal environment. The container runs as a non-root user.
- Input hygiene: invisible characters and look-alike letters are folded or reported (`sanitize_input`) before any rule runs.
- The detector that runs offline (`relay_check`) sends no data anywhere. The **arbiter** is different: it calls the model providers you configure, so your texts go to them. It runs only if you supply the judge functions.
- Container publishing is gated on the tests and on a smoke test that checks that an anonymous request is rejected with 401.

## Known limits (do not assume these are covered)
- **No TLS in the agent.** Terminate TLS in front of it (ingress, proxy). The token travels in a header.
- The rate limiter and negotiation tasks are **in memory, per process**: with several replicas the limits are per replica and tasks are lost on restart.
- `aixl_negotiate_autonomous` returns the Python **traceback** when it fails (file paths and internals), and passes the sender text as a command-line argument. It is meant for a local MCP session over stdio; do not expose it through a network-facing server.
- The envelope states what the sender sealed; it is **not signed**, so it does not authenticate the sender.
- **No penetration test, no dependency audit and no SOC 2 or similar certification** have been done. Dependency vulnerabilities in `a2a-sdk`, `mcp`, `uvicorn` and `httpx` are not monitored automatically yet.
- The tools handle whatever text you give them; if it contains personal data, that is processed in memory and (for the arbiter) sent to the model provider. Anonymise first.
- Prompt injection against the arbiter's judges was tested on a small set of attacks (documented in `docs/EVIDENCE.md`); that is not a proof of robustness.

## For deployers
See [DEPLOYMENT.md](DEPLOYMENT.md) (token, host, probes, Kubernetes secret) and [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) (the threat model for meaning-changing manipulation).

---
**En español, en breve.** Reporte vulnerabilidades a director@daralaz.com (asunto «AIXL security»), sin publicarlas antes. Es un proyecto de una sola persona: respuesta en 5 días hábiles, evaluación en 15, divulgación coordinada y como máximo a los 90 días; no hay recompensas. Solo se da soporte a la última versión de `main` y a la imagen `latest`. El agente A2A exige token fuera de loopback y no incluye TLS (hay que ponerlo delante). No se ha hecho prueba de penetración ni auditoría de dependencias.
