# AIXL — experimental semantic layer (0.5.0) — read the status first

> **Status (2026-10-03), in one paragraph.** AIXL was built as a way to represent what an instruction *means* and to check that two instructions mean the same.
> Measured on text written by **other** authors (not on the project's own benchmark), the answer for **open-domain** text is: the rule-based and LLM-encoded AIXL
> routes wrongly judge ~40–59 % of non-equivalent pairs "equivalent" (they drop whatever the closed vocabulary has no slot for), the repaired,
> safe versions prove only 0–32 % of true paraphrases, and a **strict full-text LLM arbiter (two independent models, "same" only if both agree)** recovers 99.7–100 % of
> true paraphrases with 0 % false "same" on 480 hard near-miss negatives. AIXL's remaining measured value is **narrower than first claimed**: exact, offline,
> free comparison inside a *controlled vocabulary*; deterministic input hygiene (invisible/look-alike characters); a loss detector that refuses to say "equal"
> without proof; and an interchange format with real MCP/A2A servers. Everything is in [`docs/EVIDENCE.md`](docs/EVIDENCE.md); the earlier headline
> numbers (99.4 %, 95 %+) are kept as history because they come from sets that share the translator's own vocabulary.
>
> **479 tests** pass (`.venv/bin/python -m pytest -q`). Not a standard; no production use; nothing in it executes an action.

[![tests](https://github.com/daralaz77/aixl-core/actions/workflows/tests.yml/badge.svg)](https://github.com/daralaz77/aixl-core/actions/workflows/tests.yml)

## 0. Scope of AIXL 0.5 (decided 2026-10-03, [ADR-018](docs/adr/ADR-018.md))
AIXL 0.5 is: **(1)** an exact, offline, free comparison engine *inside a controlled vocabulary*; **(2)** a loss detector that refuses to say "equal" without proof (opt-in `inconclusive`, `R:` residue, completeness); **(3)** deterministic input hygiene (`sanitize_input`); **(4)** an interchange format with real MCP/A2A servers and a bounded negotiation protocol; **(5)** an **audit layer around a full-text arbiter** (`aixl.arbiter`: versioned rules, 2-of-2 consensus, output validation, a decision memo — judges are functions you supply; the core never calls a model).
It is *not* a prover of paraphrase equivalence on open text, a candidate-pair prefilter, compression, or a standard (claims withdrawn in ADR-018).

## 1. What AIXL is
AIXL (AI Interoperability eXchange Language) is an **experimental semantic layer**: it represents what an instruction *means* (actions, targets, time, quantities, constraints, conditions, negations, references) in a canonical graph, serializes it in a compact `ATOM:VALUE` syntax, and compares two meanings. It is not a replacement for MCP, A2A, REST or JSON, and no claim of superiority over them is made or supported.

## 2. What to use for what
| You need | Use | Evidence |
|---|---|---|
| Are two **open-text** instructions the same? | A strict full-text **arbiter, 2-of-2** (two independent LLMs, "same" only if both say SAME) and a stored verdict | blind12: 359/360 recovered, **0/480** false "same" on near-misses; blind11: 100 % / 0.6 % |
| Exact, offline, free comparison in a **controlled vocabulary** | `aixl.compare` (rules route) | 0.85 ms/pair; 99.4 % on the own (same-author) benchmark; **unsafe on open text** |
| Never say "equal" without proof | `compare(..., config with "inconclusive": true)` (opt-in) | 0–2 % false "equivalent", proves 0–17 % |
| Input hygiene (invisible / look-alike characters) | `sanitize_input` (automatic) | 0 false rejections on 71 benign pairs |
| Interchange with other agents | AIXL line + MCP / A2A adapters | three vendors' clients called the MCP server |
See [docs/EVIDENCE.md](docs/EVIDENCE.md) §1 for the complete table, including what is **not** supported (e.g. AIXL as a candidate-pair prefilter: recall 15.8 % vs 60.3 % for a plain lexical filter).

## 3. Problem it tries to address
When an intention moves between models, agents or services, its meaning can change (a negation lost, `100` becoming `1000`, `Q1` becoming `Q2`) without anyone noticing. The question: *can we represent and compare meaning independently of how it was written?* The measured answer (blind10–blind12): **not with a closed-vocabulary representation on open text** — what the vocabulary has no slot for is dropped silently, which is exactly the failure to prevent; reading both texts in full does it well and cheaply (≈ $0.28 per 1 000 pairs for two judges). The product hypothesis (organizations chaining models need to verify that an intent kept its meaning across hops) is **not tested with any real organization**.

## 4. What exists
A small, local, dependency-free Python core: SemanticObject/Relation/Graph, ontology, normalizer, ES/EN/PT rule-based translator, AIXL codec (incl. the additive `R:` residue atom), comparator with `verdict` (EQUIVALENT / NOT_EQUIVALENT / INCONCLUSIVE), per-side completeness and structural-marker checks, semantic diff, drift, ambiguity and contradiction detectors, fingerprint, a bounded negotiation protocol, real MCP and A2A servers/adapters (optional dependencies), CLI, Semantic Lab (CLI + web), and the benchmark/experiment harnesses behind `docs/EVIDENCE.md`. See `ARCHITECTURE.md`.

## 5. Architecture (short)
`text → translator → SemanticGraph (canonical) → { AIXL | JSON | comparator → equivalence / diff / drift }`. AIXL is a serialization, the graph is the core. Language, semantics, protocol, encoding, transport and execution are separate layers; nothing here executes an action. The arbiter experiments (`benchmarks/`, `data/blind10/`) run outside the core: the core never calls an LLM unless `AIXL_TRANSLATOR_MODE` is set (default `rule_based`).

## 6. Install
```bash
cd ~/.claude/skills/aixl-core            # Python ≥ 3.11, no runtime dependencies
python3 -m venv .venv && .venv/bin/pip install pytest tiktoken   # dev only
```

## 7. Examples and CLI
```python
import aixl
r = aixl.compare("Analiza las ventas de Q1 2026.", "Examina las ventas del primer trimestre de 2026.")
print(r.verdict, r.equivalent, r.similarity, r.diff)   # EQUIVALENT True 1.0 []   (controlled vocabulary)
r = aixl.compare("Elimina el reporte.", "No elimines el reporte.")
print(r.equivalent, r.drift_level, r.critical_changes[0].field)   # False CRITICAL_DRIFT NEGATION
print(aixl.to_aixl("Analiza las ventas del primer trimestre de 2026"))
# V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES T:Q1-2026
print(aixl.detect_ambiguity("Analiza los datos recientes.").reason)   # VAGUE_TIME
print(aixl.detect_contradiction("Permite eliminar el reporte.", "Prohíbe eliminar el reporte.").alerts[0].type)  # ALLOW_VS_FORBID
```
**Caution:** these examples use the controlled vocabulary the translator knows. On free text the same call can say "equivalent" for pairs that differ ("to the CFO" vs "to the CEO"); use the arbiter (EVIDENCE.md §1) or turn `inconclusive` on.
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

## 8. Evidence in short (details, setups and limits: [docs/EVIDENCE.md](docs/EVIDENCE.md), [docs/adr/ADR-017.md](docs/adr/ADR-017.md))
| Set (authors) | Rules route (0.4) | AIXL LLM route + completeness | Full-text arbiter 2-of-2 |
|---|---|---|---|
| Own 5×100 (same author as code) | 99.4 % (not independent) | – | – |
| blind10 (Opus, Haiku) | 24.7–40.0 % overall; 47–51 % of non-equivalent pairs judged "equivalent" | 0–2 % false, proves 2–17 % | 56–60/60 proven, 0/180 false |
| blind11 (Sonnet; run once) | 50 % proven, **40.6 % false** | 0 % proven, 0.6 % false | **100 % proven, 0.6 % false** |
| blind12 (Opus, Sonnet; clustered, run once) | key recall 15.8 % (lexical baseline 60.3 %) | – | 359/360 proven, **0/480** near-miss false |
| Adversarial (198 pairs; red-team told the rules) | 17/70 attacks judged equivalent | – | 1/70 (injection 0/8); single Haiku 4/70 |
* Repeatability of the arbiter (82 pairs × 5 passes × 2 models): verdict flips 1.2 % (Sonnet), 6.1 % (Haiku), 1.2 % (2-of-2); errors are systematic ⇒ store the verdict.
* Cost per 1 000 pairs (estimate): deterministic compare $0 / 0.85 s; arbiter 2-of-2 ≈ $0.28; AIXL LLM encoders ≈ $1.13 (and prove 0 %).
* Rules-route ambiguity detection on free text: 16.7 % recall, 11.7 % false flags (blind11).
* AIXL is **longer** than the sentence (≈ +246 % cl100k tokens); it is not compression.
* Engineering facts (adapters, deployment, CI): unchanged and verified, see §9 and [docs/HISTORY.md](docs/HISTORY.md).

## 9. Deployment
Only the A2A agent (`aixl/agents/a2a_server.py`) is a network service; see `DEPLOYMENT.md` for the full architecture, CI/CD pipeline, Docker/Kubernetes config, monitoring strategy, critical findings and production checklist. `.github/workflows/docker-publish.yml` builds the image, **actually runs it and drives a real HTTP round-trip** before pushing to `ghcr.io/daralaz77/aixl-core`, then **pulls the just-published image back down fresh and re-verifies it** (gated on the `tests` workflow passing) — that exact sequence caught 3 real bugs before/while shipping: `a2a-sdk[http-server]` doesn't include an ASGI server (masked in CI by an unrelated transitive dependency); the AgentCard's advertised URL — not the URL used to discover it — is what real clients call back to (`AIXL_A2A_PUBLIC_URL`); and the private GHCR package had no `imagePullSecrets` wired into the Kubernetes manifest at all. **A fourth, more serious finding came from continuing to test the deployment itself, not the pipeline**: the original `replicas: 2` Deployment — written "for reliability" — silently broke `aixl_negotiate`'s multi-turn pause/resume. Measured on a real `kind` cluster: 12 of 20 resume attempts failed (`TaskNotFoundError`) because the paused-task state is per-pod and the Service has no routing awareness of it; adding session affinity fixed the common case but a real pod restart while a task was paused still lost it 100% of the time. Fixed by running `replicas: 1` (honestly trading redundancy for correctness, since there is zero production traffic today) and excluding the HPA/PDB manifests (both assumed >1 replica was safe) — DEPLOYMENT.md §8 lays out the real, not-yet-built path back to both correctness and horizontal scaling (a shared `DatabaseTaskStore`, or splitting `aixl_compare`/`aixl_negotiate` into separate deployments), deliberately left as a decision for when real traffic exists, not spec'd speculatively. **A fifth finding, from load-testing the fix itself** (DEPLOYMENT.md §9): `InMemoryTaskStore` never evicts anything — 200 real abandoned negotiations grew the agent's memory from ~60MB to ~71MB with no way back down, a real unbounded resource-exhaustion risk against a reachable endpoint. Fixed with `aixl/agents/expiring_task_store.py`'s `ExpiringTaskStore` (TTL-based sweep, default 1 hour, a new `aixl_negotiate_expired_total` metric), verified both with 4 fast unit tests and by re-running the exact 200-task scenario against a real container (memory stayed flat, a task within its TTL still converged correctly). `scripts/smoke_test_a2a.py` was also found to only ever check `aixl_compare`, not `aixl_negotiate` — fixed to cover both before the next publish. **A sixth finding, another loop (DEPLOYMENT.md §10)**: `aixl.compare()`/`aixl.to_semantic()` are CPU-bound, synchronous, called directly inside `async def execute()` — a burst of 900 concurrent calls on a 1-CPU container measurably pushed `/healthz` latency past the 3s liveness timeout in real, separate-process trials (2.45–3.27s across 3 runs). A first fix attempt (`asyncio.to_thread` alone) was tried, re-measured, and found insufficient (still spiked to 4.2s) — Python's default thread pool just moves the same GIL/CPU contention to ~32 competing threads. The real fix, `aixl/agents/concurrency.py`'s small semaphore (`AIXL_MAX_CONCURRENT_CPU_WORK`, default 4) on top of `asyncio.to_thread`, re-measured at 0.54–0.86s across 3 clean trials — consistently safe. (A first, flawed measurement of this bug ran the load generator and the health-check poller in the same Python process and read 4.5s; re-testing with them as genuinely separate OS processes corrected that number before trusting it — a methodology lesson kept honest in the writeup, not hidden.)


## 10. Limitations
See `LIMITATIONS.md` and [docs/EVIDENCE.md](docs/EVIDENCE.md) §4. The decisive ones: the closed vocabulary drops what it has no slot for; rule-based and LLM-encoded AIXL cannot prove paraphrase equivalence on open text; every number is on ES/EN/PT instruction-like text, ≤ 360 cases per set, author-assigned labels, one vendor's judge models; blind10, blind11 and blind12 are spent (any new claim needs a fresh set).

## 11. Roadmap (evidence-driven; nothing here is committed)
Done: ~~scope decision~~ (ADR-018, 2026-10-03); ~~decision memo + consensus + arbiter-output validation~~ (`aixl.arbiter`, 0.5.0).
1. **Cross-vendor judges** (GPT, Gemini, open-source) and **order-symmetry** of the arbiter on a FRESH set; embedding-based candidate blocking against the lexical baseline (untested).
2. **Default for `inconclusive`**: measure its effect on controlled-vocabulary use and decide in 0.6 whether it becomes the default.
3. Measure the product hypothesis with real agent-to-agent handoffs (does meaning change in practice, how often?).
4. ProtocolAdapters: MCP and A2A are real; REST/OpenAPI/GraphQL are not implemented; capability handshake and extension registry remain design-only.
5. If a canonical form with open role slots is ever built (ADR-016 steps 3–5), it must pass a fresh, pre-registered set against the arbiter baseline before any claim.

## Audit (master prompt §41–42) — updated 2026-10-03
| Question | Answer, with evidence |
|---|---|
| Does it really represent meaning or only match words? | **Mostly words, within a closed vocabulary.** The core compares typed elements on a canonical form, but the translator (rules or LLM-with-card) only fills the slots it knows; the rest is dropped without trace. On other authors' open text this made 40–59 % of non-equivalent pairs look equivalent (blind10/blind11). `R:` residue + completeness make the loss visible; they do not make AIXL understand it. |
| Synonyms vs real differences? | Inside the vocabulary: minimal pairs (Q1/Q2, 100/1000, do/do-not) are separated. Outside it: true synonyms (review/check, install/deploy) cannot be proven equal by any AIXL route tested (≤ 32 %); the full-text arbiter does it (99.7–100 %). |
| Negation, quantity, date, condition, restriction preserved? | Through serialization of what was captured: 100 %. Captured from open text: not reliably (see EVIDENCE.md); the arbiter caught 0/480 near-misses wrongly. |
| Is the problem it targets real? | Untested with real agent traffic; the failure mode itself (meaning changing across hops) is what the blind sets reproduce synthetically. |
| Is it better than alternatives? | For open-text equivalence a strict LLM judge pair is better and cheap. AIXL has no measured advantage there. Cost scaling favours canonical keys only for exact matching in controlled vocabularies. |
| Is it safe against tampering? | Input obfuscation is handled deterministically; the arbiter resisted 8/8 injection pairs; semantic tampering is flagged by the rules route inside the vocabulary (450/450 combinatorial, 54/57 hard critical — own, same-author suite). Not defended: context poisoning, provenance spoofing, replay, capability spoofing. |
