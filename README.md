# AIXL 0.3 — Semantic Core & Semantic Equivalence Engine (MVP)

[![tests](https://github.com/daralaz77/aixl-core/actions/workflows/tests.yml/badge.svg)](https://github.com/daralaz77/aixl-core/actions/workflows/tests.yml)

## 1. What AIXL is
AIXL (AI Interoperability eXchange Language) is an **experimental semantic layer**: it represents what an instruction *means* (actions, targets, time, quantities, constraints, conditions, negations, references) in a canonical graph, serializes it in a compact `ATOM:VALUE` syntax, and compares two meanings. It is not a replacement for MCP, A2A, REST or JSON, and no claim of superiority over them is made or supported.

## 2. Problem it tries to address
When an intention moves between models, agents or services, its meaning can change (a negation lost, `100` becoming `1000`, `Q1` becoming `Q2`) without anyone noticing. AIXL 0.3 asks: *can we represent and compare meaning independently of how it was written?* (product hypothesis: organizations chaining several models need to verify that an intent kept its meaning across hops — **not tested with any real organization**).

## 3. What 0.3 is
A small, local, dependency-free Python core (no external AI API needed) with: SemanticObject/Relation/Graph, ontology, normalizer, ES/EN/PT rule-based translator, AIXL codec, comparator, semantic diff, drift, ambiguity and contradiction detectors, a live negotiation protocol, real MCP and A2A server/adapters (both optional dependencies), CLI, Semantic Lab (CLI + web), benchmarks and 170 tests. See `ARCHITECTURE.md`.

## 4. Architecture (short)
`text → translator → SemanticGraph (canonical) → { AIXL | JSON | comparator → equivalence / diff / drift }`. AIXL is a serialization, the graph is the core. Language, semantics, protocol, encoding, transport and execution are separate layers; nothing here executes an action.

## 5. Install
```bash
cd ~/.claude/skills/aixl-core            # Python ≥ 3.11, no runtime dependencies
python3 -m venv .venv && .venv/bin/pip install pytest tiktoken   # dev only
```

## 6. Examples
```python
import aixl
r = aixl.compare("Analiza las ventas de Q1 2026.", "Examina las ventas del primer trimestre de 2026.")
print(r.equivalent, r.similarity, r.diff)        # True 1.0 []
r = aixl.compare("Elimina el reporte.", "No elimines el reporte.")
print(r.equivalent, r.drift_level, r.critical_changes[0].field)   # False CRITICAL_DRIFT NEGATION
print(aixl.to_aixl("Analiza las ventas del primer trimestre de 2026"))
# V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES T:Q1-2026
print(aixl.detect_ambiguity("Analiza los datos recientes.").reason)   # VAGUE_TIME
print(aixl.detect_contradiction("Permite eliminar el reporte.", "Prohíbe eliminar el reporte.").alerts[0].type)  # ALLOW_VS_FORBID
```

## 7. CLI
```bash
python cli.py translate "Analiza las ventas de Q1 2026"
python cli.py compare "Analiza las ventas de Q1 2026" "Examina las ventas del primer trimestre de 2026"
python cli.py diff "Analiza las ventas de Q1 2026" "Analiza las ventas de Q2 2026"
python cli.py drift "Analiza las ventas de Q1 2026" "Analiza las ventas de Q2 2026"
python cli.py ambiguity "Analiza los datos recientes."      # also: contradiction, aixl, lab, demo, bench
python cli.py serve 8765                                     # Semantic Lab web app -> http://localhost:8765
python cli.py negotiate "Close ticket #77." "Delete ticket #77."   # also: negotiate-aixl [--rounds N] [--json]
python cli.py mcp-serve                                       # real MCP server over stdio; needs `pip install .[mcp]`
python -m aixl.agents.a2a_server 8766                          # real A2A agent over HTTP; needs `pip install .[a2a]`
```

## 8. Benchmark
See `BENCHMARK.md`. Method: pre-registered; independent blind authors; each fresh set evaluated once before tuning; contaminated numbers labelled.

## 9. Results (summary; details and caveats in BENCHMARK.md)
* Rule-based translator on FRESH blind sets: accuracy **72 → 80 → 76 → 76 %** (precision 88–95 %, recall 51–63 %). **S1 (≥ 90 %) not met by the rule-based route.**
* Same core fed by an LLM translator following the card (Haiku 4.5 / Sonnet 5), fresh set 4: **96.0 % / 96.5 %** accuracy, critical drift 96.8 %. S1 and S2 met on that set; single pass. Cross-vendor E-XV (set 5, pairs written by Gemini and ChatGPT; encoders Haiku, Sonnet, Gemini, ChatGPT): 96.5 / 96.5 / 95.0 / 93.5 %, rule-based 78.5 %; see BENCHMARK.md §7. Codec fixed after E-XV; confirmed on fresh set 6 (E-CODEC, BENCHMARK.md §8): 0/200 parse failures, Sonnet 94.0 % accuracy. Date/time/duration/reference gaps closed over 3 iteration rounds and confirmed on fresh set 9 (E-DATE, BENCHMARK.md §9): Sonnet 95.0 %, 0 parse failures, 39/39 critical drift; rule-based 88.0 %. Cross-vendor ENCODING consistency E-INTEROP (BENCHMARK.md §10): 53 % baseline -> **79 %** after 3 rounds of shared vocabulary + a tie-break rule. Live negotiation protocol E-NEGOTIATE (BENCHMARK.md §11): 21/21 real remaining disagreements converge via a bounded clarification exchange, verified with a real 2-model live demo, and wired into the CLI/API (`cli.py negotiate` / `negotiate-aixl`). Real protocol adapter E-MCP (BENCHMARK.md §12): `MCPAdapter` + a real running MCP server, validated against the official `mcp` SDK's own models and exercised by a real subprocess + real client round-trip (4/4), not a mock — and confirmed by THREE independent vendors' clients, ALL 3 tools on ALL 3: Claude Desktop (Anthropic), ChatGPT/Codex (OpenAI) and Antigravity CLI (Google), each registered via its own config format/CLI command and each getting the correct result on every tool, matched by this project's own reproduction. **Autonomous 2-process negotiation E-AUTONOMOUS** (BENCHMARK.md §13): a real sender agent (its own OS process) and a receiver driver exchange NEGOTIATE turns over real MCP stdio with zero human relay — re-measured the real 21 E-INTEROP disagreements this way: 21/21 converge, identical to the single-process number. Wired into the real server as `aixl_negotiate_autonomous`: a real MCP client calling this one tool makes the server itself spawn a genuinely separate third process and negotiate with it. **E-MCP-DESTRUCTIVE** (BENCHMARK.md §14): the real Claude Desktop retest confirmed a prior env/cwd fix AND raised a genuine gap — a destructive-action disagreement (e.g. UPDATE vs DELETE) was auto-resolved by trusting the sender with no signal DELETE is irreversible, even though `aixl_compare` already flags it CRITICAL. Fixed with a narrow `irreversible_actions` config list (DELETE only, after a broader first attempt broke 8 tests); re-measured the real 21 E-INTEROP disagreements: now 20/21 converge (was 21/21) — a genuine correction (Gemini had misread "excluir" as DELETE in the one case that now correctly REJECTs), not a regression. **Widened to EXECUTE and SEND at the user's request**: re-measured again, **18/21** — SEND's addition caught a genuine over-extraction bug, EXECUTE's one affected case is more debatable (a translator vocabulary quirk, not clearly a dangerous disagreement); reported honestly rather than declared settled. A wider search of the independent 200-pair E-XV corpus confirmed the split (8 of 10 real EXECUTE instances across both datasets are the same vocabulary quirk; SEND found 2 more genuine supporting cases) — **EXECUTE removed, SEND kept**; final re-measurement: **19/21** converge. **Second real protocol adapter E-A2A** (BENCHMARK.md §15): `A2AAdapter` + a real running A2A agent (official Google `a2a-sdk`, JSON-RPC over HTTP — a genuinely different transport from MCP's stdio), validated against the SDK's own protobuf `Message` type and exercised by a real subprocess + real client round-trip (3/3), not a mock. Reading the SDK first (before writing code) surfaced a real architectural difference: A2A's model is built for long-running, stateful tasks, materially heavier than MCP's simple synchronous call — scoped honestly to the one workflow this needed (an immediate reply, no Task lifecycle). **Negotiation as a native multi-turn A2A Task E-A2A-NEGOTIATE** (BENCHMARK.md §16): instead of treating A2A's heavier Task model as a cost to avoid, gave it the one AIXL capability that genuinely needs it — `aixl_negotiate` now pauses a real Task (`TASK_STATE_INPUT_REQUIRED`) and asks a human when a disagreement involves an irreversible action, resuming correctly with their answer; makes real a claim (`negotiate()`'s "requires human confirmation" REJECT message) that previously had no actual mechanism behind it. Two real bugs found by running the round-trip, not by reading the code, both fixed: the human's answer wasn't applied to the sender's own value (so resuming kept repeating the same question); the irreversible-check was ordered before the empty-sender-value check (the same mistake made and fixed earlier the same day merging `negotiate()`/`negotiate_autonomous_async()`). 170/170 tests.
* Critical-drift detection (negation, quantity, time, constraint, condition, reference): 89.6–97.0 % rule-based, 96.8–100 % LLM route.
* Ambiguity (n = 20, first run) 90 %; contradiction (n = 20, first run) 75 %.
* AIXL is **longer** than the sentence (≈ +130 % characters, ≈ +246 % cl100k tokens); 64 % fewer tokens than canonical JSON.
* Tests: 170 passed (154 core + 16 A2A, skip cleanly if `a2a-sdk` isn't installed). Dev 200-case set: 100 % — DEMO only. CI (`.github/workflows/tests.yml`) runs the full suite on every push/PR across Python 3.11 and 3.12 — added 2026-09-30 and caught a real bug on its first run: an f-string with backslashes in `aixl/legacy02/core/encoder.py` was only valid from Python 3.12 on (PEP 701), silently working in local dev (always run on 3.14) but a hard `SyntaxError` on the project's declared floor (3.11); fixed and reverified on a real Python 3.11 install.

## 10. Limitations
See `LIMITATIONS.md` (fixed vocabulary, flat frame, no clock for relative dates, single-annotator labels, weak conditions/negation scope, Anthropic-only encoders tested).

## 11. Roadmap → AIXL 0.4 (Semantic Interoperability Layer) — only if evidence supports it
1. **Cross-vendor encoder test** (GPT, Gemini, open-source) on a fresh blind set authored by a non-Anthropic model — the largest threat to the current result.
2. Per-action targets in the graph (fix the swap blind spot) and a reference clock for relative dates.
3. Adjudicated labels (≥ 2 annotators, κ) on a 300-pair set incl. hard real agent handoffs.
4. Measure the product hypothesis: log real agent-to-agent handoffs and count meaning changes (does the problem occur? how often?).
5. ProtocolAdapter implementations: MCP (BENCHMARK.md §12) and A2A (BENCHMARK.md §15) done — both real SDKs, real servers, real subprocess round-trips; REST/OpenAPI/GraphQL still not implemented. A semantic-firewall prototype (`explain()` is the groundwork) remains future work.

## 12. Deployment
Only the A2A agent (`aixl/agents/a2a_server.py`) is a network service; see `DEPLOYMENT.md` for the full architecture, CI/CD pipeline, Docker/Kubernetes config, monitoring strategy, critical findings and production checklist. `.github/workflows/docker-publish.yml` builds the image, **actually runs it and drives a real HTTP round-trip** before pushing to `ghcr.io/daralaz77/aixl-core`, then **pulls the just-published image back down fresh and re-verifies it** (gated on the `tests` workflow passing) — that exact sequence caught 3 real bugs before/while shipping: `a2a-sdk[http-server]` doesn't include an ASGI server (masked in CI by an unrelated transitive dependency); the AgentCard's advertised URL — not the URL used to discover it — is what real clients call back to (`AIXL_A2A_PUBLIC_URL`); and the private GHCR package had no `imagePullSecrets` wired into the Kubernetes manifest at all. **A fourth, more serious finding came from continuing to test the deployment itself, not the pipeline**: the original `replicas: 2` Deployment — written "for reliability" — silently broke `aixl_negotiate`'s multi-turn pause/resume. Measured on a real `kind` cluster: 12 of 20 resume attempts failed (`TaskNotFoundError`) because the paused-task state is per-pod and the Service has no routing awareness of it; adding session affinity fixed the common case but a real pod restart while a task was paused still lost it 100% of the time. Fixed by running `replicas: 1` (honestly trading redundancy for correctness, since there is zero production traffic today) and excluding the HPA/PDB manifests (both assumed >1 replica was safe) — DEPLOYMENT.md §8 lays out the real, not-yet-built path back to both correctness and horizontal scaling (a shared `DatabaseTaskStore`, or splitting `aixl_compare`/`aixl_negotiate` into separate deployments), deliberately left as a decision for when real traffic exists, not spec'd speculatively. **A fifth finding, from load-testing the fix itself** (DEPLOYMENT.md §9): `InMemoryTaskStore` never evicts anything — 200 real abandoned negotiations grew the agent's memory from ~60MB to ~71MB with no way back down, a real unbounded resource-exhaustion risk against a reachable endpoint. Fixed with `aixl/agents/expiring_task_store.py`'s `ExpiringTaskStore` (TTL-based sweep, default 1 hour, a new `aixl_negotiate_expired_total` metric), verified both with 4 fast unit tests and by re-running the exact 200-task scenario against a real container (memory stayed flat, a task within its TTL still converged correctly). `scripts/smoke_test_a2a.py` was also found to only ever check `aixl_compare`, not `aixl_negotiate` — fixed to cover both before the next publish.

## Audit (master prompt §41–42)
| Question | Answer, with evidence |
|---|---|
| Does it really represent meaning or only match words? | **Both, by layer.** The core compares structured, typed elements (action, target, period, quantity, negation...) on a canonical form, not strings. But the rule-based translator IS lexicon/pattern matching; where the lexicon does not cover a phrase it silently drops it (recall 51–63 % on fresh paraphrases). With an LLM translator the same core reached 96 %. |
| Synonyms vs real differences? | Minimal pairs (Q1/Q2, 100/1000, do/do-not, >= vs >) are separated (precision 88–100 %); synonyms converge only inside the covered vocabulary. |
| Negation, quantity, date, condition, restriction preserved? | Through serialization: 100 %. Captured from text: rule-based ~60–95 % per category on fresh sets (negation weakest, 60 %), LLM route higher. Conditions beyond count/existence/containment/confidence are weak literals. |
| Ambiguity detected? | 90 % on 20 blind items (heuristic; first run). |
| Differences explainable? | Yes: field, source, target, kind, severity, drift level, human diff. |
| Reproducible? | Rule-based route fully deterministic; blind data and first-run results are frozen (read-only) with checksums. The LLM route depends on stored model outputs. |
| Works without an external API? | Yes (rule-based route); accuracy on unseen phrasing is the price. |
| DEMO vs EVIDENCE vs REAL VALIDATION | DEMO: 6 demos, dev-200, tests. EVIDENCE: blind first runs (sets 1–4), E-LLM on set 4, cross-vendor E-XV on set 5, codec-fix confirmation E-CODEC on set 6, date/time/duration/reference fixes E-DATE on set 9, cross-vendor ENCODING-consistency E-INTEROP (53%→79%), the E-NEGOTIATE live negotiation protocol (21/21 real disagreements resolved, one real 2-model live demo), E-MCP's own subprocess round-trip (4/4), E-AUTONOMOUS (21/21 real disagreements re-resolved through two genuinely separate OS processes, no human relay), and E-A2A's own subprocess + real client round-trip over a second real protocol/transport (3/3). REAL VALIDATION: THREE independent vendors' MCP clients this project never authored, each confirmed on ALL 3 tools (`aixl_compare`/`aixl_negotiate`/`aixl_translate`) — Claude Desktop (Anthropic), ChatGPT/Codex (OpenAI), Antigravity CLI (Google) — connected to the real server and got correct results on 2026-09-30 (`BENCHMARK/results_mcp_desktop_*.md`, `results_mcp_second_client_codex_FIRST_RUN.md`, `results_mcp_third_client_antigravity_FIRST_RUN.md`). Still n=1 per tool per client for MCP, and no independent third-party client has connected to the A2A agent yet; no real organization's production handoffs have touched this. |
