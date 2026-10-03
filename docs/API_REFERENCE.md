# API reference

There are four surfaces: the **Python API** (primary), the **MCP server**, the **A2A agent**, and the **Semantic Lab** web app. The REST API of
master prompt §32 (`POST /encode`, `/decode`, …) is **not implemented**; use the Python API or wrap it.

## 1. Python API — `import aixl` (`aixl/api/service.py`)
| Function | Returns | Notes |
|---|---|---|
| `to_semantic(text)` | `SemanticGraph` | text → graph |
| `to_aixl(text)` | `str` | text → AIXL line |
| `from_aixl(line)` | `SemanticGraph` | raises `AixlError` (`INVALID_AIXL`, `VERSION_MISMATCH`) |
| `translate(text)` | `dict` | `input, semantic (canonical), graph, aixl, ambiguity, warnings` |
| `compare(a, b, config=None)` | `ComparisonResult` | `.verdict .equivalent .similarity .drift_level .differences .critical_changes .warnings .to_dict()`; `.verdict` is `INCONCLUSIVE` only with `config["inconclusive"]` on |
| `compare_aixl(a, b, config=None)` | `ComparisonResult` | same, on two AIXL lines |
| `semantic_diff(a, b)` | `str` | human-readable `SEMANTIC DIFF` |
| `detect_drift(source, target)` | `DriftReport` | `.level .critical .differences`; `critical` ⇔ `CRITICAL_DRIFT` |
| `detect_ambiguity(text)` | `AmbiguityResult` | `.ambiguous .fields .reason .findings .notes` |
| `detect_contradiction(a, b)` | `ContradictionResult` | `.contradiction .alerts[type, detail]` |
| `negotiate(sender_text, receiver_text, max_rounds=3, today=None)` | `NegotiationOutcome` | `.converged .rounds .transcript .remaining_differences` |
| `negotiate_aixl(aixl_sender, aixl_receiver, …)` | `NegotiationOutcome` | same, on two AIXL lines |
| `semantic_fingerprint(text, config=None, today=None)` | `str` (16 hex) | pass `today` for cross-day reproducibility |
| `semantic_fingerprint_aixl(line, …)` | `str` | |
| `explain(text)` | `dict` | `wants, objects, constraints, conditions, modality, ambiguous` (groundwork only; no enforcement) |

Example (the `to_dict()` of a one-field difference):
`compare("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026.").to_dict()` →
`{"equivalent": false, "drift_level": "MAJOR_DRIFT", "differences": [{"field": "TIME", "source": "Q1-2026", "target": "Q2-2026", "kind": "changed", "severity": "MAJOR"}], …}`.
Pass `today=datetime.date(...)` wherever relative time matters and you need reproducible results.

## 2. MCP server (`python -m aixl.mcp_server`, or `python cli.py mcp-serve`; needs `pip install .[mcp]`)
Official `mcp` SDK, stdio JSON-RPC. Tools (thin wrappers over the Python API, no new semantics):
`aixl_translate(text)` → `{aixl, semantic, ambiguous}` · `aixl_compare(a, b)` → `ComparisonResult.to_dict()` ·
`aixl_negotiate(sender_text, receiver_text, max_rounds=3)` → `{converged, rounds, transcript, remaining_differences}` ·
`aixl_negotiate_autonomous(...)` → spawns a separate sender-agent process and negotiates over real MCP stdio.
Confirmed with real Claude Desktop, ChatGPT/Codex and Antigravity clients (BENCHMARK.md §12).

## 3. A2A agent (`python -m aixl.agents.a2a_server 8766`; needs `pip install .[a2a]`)
Official `a2a-sdk`, JSON-RPC over HTTP, agent card `aixl-core`. Skills: `aixl_compare` (immediate reply) and `aixl_negotiate` (a multi-turn Task that
pauses in `INPUT_REQUIRED` and asks a human when the dispute involves an irreversible action). Streaming is off.

## 4. Semantic Lab web app (`python cli.py serve [port]`, default 8765, 127.0.0.1)
Stdlib HTTP server for demos only: `GET /` (UI) and `POST /api/compare` with `{"a": "...", "b": "..."}` (each ≤ 2000 chars). Not a production API.

## Errors and stability
`AixlError(code)` is the only protocol exception. Result shapes are stable within a MINOR version ([VERSIONING_POLICY.md](VERSIONING_POLICY.md)); the
`warnings` key of `ComparisonResult.to_dict()` appears only when non-empty.

## validate / round_trip (added 2026-10-02)
- `validate(text_or_graph) -> ValidationResult{status: VALID|INVALID|VALID_WITH_WARNINGS, issues[{code, severity, where, message}]}`. Codes: INVALID_SCHEMA UNKNOWN_TYPE INVALID_RELATION MISSING_REQUIRED_FIELD CONTRADICTION INVALID_TIME INVALID_QUANTITY SEMANTIC_LOSS. Errors => INVALID; warnings (e.g. unrecognised noun, no action) => VALID_WITH_WARNINGS.
- `round_trip(text_or_graph) -> RoundTripResult{preserved, fidelity, aixl, differences, error}`. Fidelity = mean per-dimension agreement after text->graph->AIXL->graph; it measures encoding loss only, not extraction accuracy.
- Node `provenance`: EXPLICIT (stated), INFERRED (derived INTENT/GOAL), MODEL_DERIVED (LLM/local route, via `mark_model_derived`). RESOLVED and EXTERNAL_CONTEXT are valid values but nothing produces them yet.

## Module-level functions not exported by `import aixl` (2026-10-02/03)
* `aixl.core.completeness.check_completeness(text, graph)` → `{complete, unaccounted, unreflected_markers, markers}`; `annotate(graph, text)` stores it in `graph.meta["completeness"]` so `compare_graphs(..., {"inconclusive": True})` can use it; `extract_markers(text)`, `marker_conflicts(a, b)`.
* `aixl.core.lexicon_gaps.unaccounted_content(text, graph)` and `residue_key(clauses)`.
* Not part of the library: the arbiter, funnel and repeatability experiments are harnesses in `benchmarks/` (`blind11_eval`, `funnel_eval`, `repeatability_eval`, `arbiter_eval`, `adversarial_eval`); the core never calls an LLM unless `AIXL_TRANSLATOR_MODE` is `llm`/`auto`/`local`.
**Which call answers "do these two open-text instructions mean the same?"** None of the functions above, on their own: see the recommendation in [EVIDENCE.md](EVIDENCE.md) §1 (full-text arbiter, 2-of-2).
