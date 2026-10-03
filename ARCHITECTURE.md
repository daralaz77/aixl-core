# AIXL 0.3 — Architecture

> **Scope note (2026-10-03).** This document describes the *structure* of the core, which is accurate. It does **not** say how well the core understands text: on other authors' open-domain text the closed-vocabulary translator drops what it has no slot for, so the core is exact only inside its vocabulary. The semantic judgment "do these two open-text instructions mean the same?" lives **outside** the core (a full-text arbiter, see [docs/EVIDENCE.md](docs/EVIDENCE.md)); the core never calls an LLM unless `AIXL_TRANSLATOR_MODE` is set.

## Layers (never mixed)
```
LANGUAGE   natural text (ES/EN/PT)                     "how it is said"
   │  aixl/translators/natural_to_semantic.py  (rule-based, replaceable by any model)
SEMANTICS  SemanticGraph + canonical form              "what it means"   aixl/core/*
   │  aixl/serialization/{aixl_codec,json_codec}.py
ENCODING   AIXL 0.3 (compact)  |  JSON (debug/interchange)
   │  aixl/adapters/protocol_adapter.py   (AixlAdapter/JsonAdapter/MCPAdapter/A2AAdapter real; REST/OpenAPI/GraphQL not implemented)
PROTOCOL / TRANSPORT  aixl/mcp_server.py (official `mcp` SDK, stdio) and aixl/agents/a2a_server.py (official `a2a-sdk`, JSON-RPC/HTTP)
EXECUTION  — out of scope for 0.3 (nothing here executes an action)
```
Rule: the **Semantic Core is the graph**. AIXL is only a serialization of it; changing the AIXL syntax must not change meaning.

## Modules (aixl/)
| Module | Role |
|---|---|
| `core/semantic_object.py` | `SemanticObject(id, type, value, attributes, confidence, source)` — confidence = extraction confidence, not truth |
| `core/semantic_relation.py` | `SemanticRelation(source, relation, target)`; relations TARGET ACTOR OBJECT SOURCE RESULT CAUSE CONDITION CONSTRAINT REFERENCE DEPENDS_ON BEFORE AFTER EQUIVALENT CONTRADICTS (+ TIME LOCATION OUTPUT MODIFIER QUANTITY INTENT) |
| `core/semantic_graph.py` | nodes/edges, `from_frame/to_frame` (bridge to the AIXL frame), `canonical()` (16 dimensions, incl. `bindings` and `residue`), JSON |
| `core/ontology.py` | controlled ontology (ACTION/ENTITY/DATA/TIME/MODIFIER), antonyms, `load_config()` |
| `core/normalizer.py` | closed lexicons: extension verbs, units, aggregates, formats; number/time/action normalization; no fuzzy matching |
| `core/comparator.py` | layered comparison on canonical forms; differences with severity; similarity (weighted, configurable); human `SEMANTIC DIFF` |
| `core/lexicon_gaps.py` | out-of-lexicon noun warnings (`UNRECOGNIZED_TERMS`), `unaccounted_content()` (content words no slot accounts for), `residue_key()` (canonical form of `R:` residue) — never changes a graph, only reports (added 2026-10-02) |
| `core/completeness.py` | per-side completeness of an encoding + closed structural-marker lexicon (before/after, only, all, except, not, more/less than, every); feeds the opt-in INCONCLUSIVE verdict in the comparator (added 2026-10-03) |
| `core/fingerprint.py` | `semantic_fingerprint()`: SHA-256[:16] of `canonical()`; exact-duplicate key, not a paraphrase detector (docs/FINGERPRINT.md) |
| `core/validator.py`, `core/roundtrip.py` | `validate()` structured issues; `round_trip()` encoding fidelity |
| `core/drift.py` | drift level from the worst difference; CRITICAL_SEMANTIC_DRIFT flag |
| `core/ambiguity.py` | blocking reasons (PRONOUN_NO_ANTECEDENT, MULTIPLE_POSSIBLE_REFERENTS, VAGUE_TIME, MISSING_YEAR, MISSING_TARGET, UNSPECIFIED_SCOPE, MISSING_COMPARAND, UNRESOLVED_REFERENT, AMBIGUOUS_MODALITY) + INFO notes |
| `core/contradiction.py` | explicit opposition on the SAME object: request vs forbid, allow vs forbid, ENABLE/DISABLE, INCLUDE/EXCLUDE, PUBLIC/PRIVATE, BEFORE/AFTER, step order |
| `translators/*` | text→graph, graph→AIXL, AIXL→graph |
| `serialization/*` | AIXL codec (uses the vendored, measured 0.2 parser/encoder), JSON codec |
| `api/service.py` | public API: translate, to_semantic, to_aixl, from_aixl, compare, compare_aixl, semantic_diff, detect_drift, detect_ambiguity, detect_contradiction, negotiate, negotiate_aixl (+ `explain` for future semantic-firewall use) |
| `legacy02/` | vendored AIXL 0.2 analyzer/codec (measured in the aixl-translator skill), patched where documented in CHANGELOG |
| `negotiation.py` | E-NEGOTIATE (2026-09-30): a bounded clarification exchange between two agents when their independent AIXL encodings of the same instruction disagree — its OWN wire format (`NEGOTIATE X=...`), separate from the semantic ATOMS; carries an AIXL line as payload where relevant, decoded by the unmodified `serialization/aixl_codec`. Measured 21/21 real E-INTEROP disagreements converge; see BENCHMARK.md §11. |
| `mcp_server.py` | E-MCP (2026-09-30): a REAL running MCP server (official `mcp` SDK, stdio transport) exposing `aixl_translate`/`aixl_compare`/`aixl_negotiate`/`aixl_negotiate_autonomous` as thin wrappers over `api/service.py`/`autonomous_negotiation.py` — the first non-`NotImplementedError` protocol adapter target. `cli.py mcp-serve` starts it; needs the optional `mcp` extra (`pip install .[mcp]`). See BENCHMARK.md §12. |
| `agents/sender_agent.py` | E-AUTONOMOUS (2026-09-30): a real, standalone MCP server playing the SENDER side of a negotiation — a genuinely separate OS process. Answers CLARIFY questions recomputed fresh from its own stored source (`--text` or `--aixl`) on every call, never cached at setup. |
| `autonomous_negotiation.py` | E-AUTONOMOUS (2026-09-30): `negotiate_autonomous()`/`negotiate_autonomous_async()` spawn `agents/sender_agent.py` as a genuine subprocess and drive a REQUEST→CLARIFY→ANSWER→ACCEPT/REJECT exchange over real MCP stdio with zero human relay — reuses `negotiation.py`'s tested turn logic (imported, not reimplemented; `negotiate()` itself untouched). Re-measured 21/21 real E-INTEROP disagreements this way; wired into `mcp_server.py` so a real MCP client can trigger it directly. See BENCHMARK.md §13. |
| `agents/a2a_server.py` | E-A2A (2026-09-30): a REAL running A2A agent (official Google `a2a-sdk`, JSON-RPC over HTTP, `starlette`+`uvicorn`) exposing two skills, `aixl_compare` (immediate-response Message) and `aixl_negotiate` (a genuine multi-turn Task — see below), over the actual Agent2Agent protocol — the second real protocol adapter target after MCP. `python -m aixl.agents.a2a_server [PORT]` starts it; needs the optional `a2a` extra (`pip install .[a2a]`). See BENCHMARK.md §15. |
| `agents/a2a_negotiate.py` | E-A2A-NEGOTIATE (2026-09-30): `aixl_negotiate` as a native multi-turn A2A Task, not a single reply — uses `TaskState.TASK_STATE_INPUT_REQUIRED` to pause and ask a human exactly when a disagreement involves an irreversible action (closing a gap `negotiate()`'s own REJECT message had always claimed but never mechanized), resuming correctly with their answer. Reuses `aixl.negotiation`'s tested helpers (imported, not reimplemented); `negotiate()` itself untouched. See BENCHMARK.md §16. |

## Canonical form (what equivalence compares)
`intent, actions (ordered), entities, data, time, location, constraints, conditions, negation (FORBID:/ALLOW: per action), references, quantities, goal, output, modifiers, bindings, residue` (`bindings` added 2026-10-02: ACTION>ARG pairs for 2+ action texts; empty = unknown. `residue` added 2026-10-02: order-free stemmed content words of the `R:` clauses an encoder could not place in any slot; empty = none declared). `intent` and `goal` are derived from actions/negation/entities and are scored but never reported as independent differences.

## AIXL 0.3 encodings (extensions to the 0.2 atoms, all measured for parse-ability)
`K:QTY=100:RECORDS` · `N:NO_X K:FORBID_X` (prohibition) · `K:ALLOW_X` · `D:TOTAL_/AVERAGE_/COUNT_x` · `F:COUNT>100:RECORDS` · `F:X_EXISTS` · `F:CONTAINS:X` / `F:NOT_CONTAINS:X` · `K:VISIBILITY=PUBLIC|PRIVATE` · `K:BEFORE=`/`K:AFTER=` · `Y:@NAME` · `K:SELECT=FIRST|LAST` · `K:WITHOUT=X` · `P:URGENT|HIGH|LOW` · `A:UNSPECIFIED` for allow/forbid of an unlisted action · `R:"clause",…` (additive 2026-10-02) residue the encoder could not express, kept in the text's own words.

## ASSUMPTIONS (minimal, reversible, documented)
1. Kept the 0.2 intent/goal vocabulary (REQUEST_EXECUTION for DELETE, not REQUEST_DELETE) — it was validated across five models.
2. Prohibition is encoded `N:NO_X K:FORBID_X` (0.2 rule), not `N:FORBID`.
3. Ontology decides node type: REPORT/DOCUMENT/MODEL/RESULT/EVENT... are ENTITIES (AIXL `E:`), SALES/CUSTOMERS/USERS/DATASET... are DATA (`D:`).
4. Equivalence = exact canonical equality. Similarity is a graded metric for non-equivalent pairs only.
5. Action groups (CREATE≡GENERATE, GET≡RETRIEVE, SEARCH≡FIND, CHECK≡VALIDATE) are equivalent for comparison (config `action_groups`, empty list = strict).
6. TIME change severity = MAJOR (the two user specs disagree: CRITICAL in one, MODERATE in an example of the other). Configurable in `data/config.json`.
7. `EXCLUDE X` ≡ `FORBID INCLUDE X` in the canonical form (the graph keeps the surface verb).
8. *(Superseded 2026-09-27, E-DATE.)* Relative days/months/years now resolve against an explicit `today` (default: system date) at canonicalization, so "mañana" equals the matching ISO date; weeks stay unresolved on purpose. Originally: relative dates were not resolved (no clock).
9. A generic `DATA` mention is dropped when a specific datum is present ("datos de ventas" = SALES).

## Future integration (not implemented)
`ProtocolAdapter.encode/decode/validate` with reference `AixlAdapter`, `JsonAdapter` and, since 2026-09-30, two REAL ones: `MCPAdapter` (validated against the official `mcp` SDK's own pydantic models, backed by a real running server in `aixl/mcp_server.py` — see BENCHMARK.md §12) and `A2AAdapter` (validated against the official `a2a-sdk`'s own protobuf `Message` type, backed by a real running HTTP agent in `aixl/agents/a2a_server.py` — see BENCHMARK.md §15). `RESTAdapter, OpenAPIAdapter, GraphQLAdapter` still raise `NotImplementedError`. `explain(text)` returns what the agent wants, on which object, under which constraints, allowed/forbidden — groundwork for a semantic firewall (no enforcement in 0.3).

## Decision record added 2026-10-03
10. **The core is exact within its vocabulary and loss-aware outside it; it does not judge open-text paraphrase.** Evidence: [docs/EVIDENCE.md](docs/EVIDENCE.md), [docs/adr/ADR-016.md](docs/adr/ADR-016.md), [docs/adr/ADR-017.md](docs/adr/ADR-017.md). `inconclusive` (opt-in, default off) makes the comparator refuse "equal" without proof; the arbiter harness (`benchmarks/`) is outside the library by design.
