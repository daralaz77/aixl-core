# Architecture audit — aixl-core (2026-09-30)

Senior-engineer reverse-engineering pass requested by the user: understand the full data flow, find bad
architecture decisions / duplicated logic / bottlenecks / scalability risks / maintainability problems,
report a clean breakdown + refactor strategy, and improve code quality **without changing functionality**.
Every change below was verified against the full test suite and, where it touches the translator or
negotiation logic, against the real benchmarks too — the same evidence discipline the rest of this
project uses.

## 1. Data flow (as it actually is, not as documented)

```
text (ES/EN/PT)
  -> aixl/translators/natural_to_semantic.py : to_graph()
       - regex-driven, ~450 lines, many sequential stages (action, target, entities,
         quantities, time, output format, visibility, "without X" constraint, ...)
       - imports aixl/legacy02/translators/natural_to_semantic.py as `legacy`
         (0.2 base: ACTION_RX / DATA_RX / ENTITY_RX / analyze())
       - imports aixl/core/normalizer.py (0.3 extensions: EXTRA_ACTION_RX, FORBID_CUE,
         ALLOW_CUE, AGG_MAP, OUTPUT_ALIASES, SemanticNormalizer)
  -> aixl/core/semantic_graph.py : SemanticGraph (the canonical form — this is the real core)
  -> branches from the canonical graph:
       a) aixl/serialization/aixl_codec.py       encode/decode <-> AIXL wire syntax
       b) aixl/core/comparator.py                compare_canonical() -> ComparisonResult
       c) aixl/core/ambiguity.py                 detect_ambiguity_graph()
  -> aixl/negotiation.py            negotiate()              single-process, in-memory sender dict
  -> aixl/autonomous_negotiation.py negotiate_autonomous_async()  2 real OS processes over MCP stdio,
                                                                    spawns aixl/agents/sender_agent.py
  -> aixl/mcp_server.py             the 4 real MCP tools (translate, compare, negotiate, negotiate_autonomous)
  -> aixl/adapters/protocol_adapter.py  ProtocolAdapter ABC: AixlAdapter/JsonAdapter/MCPAdapter (real),
                                          A2A/REST/OpenAPI/GraphQL (explicit _NotImplementedAdapter stubs)
  -> cli.py, lab/render.py, lab/server.py   human-facing CLI + tiny web viewer
```

Config (`data/config.json`, loaded via `aixl.core.ontology.load_config()`) holds severity thresholds,
`destructive_actions` (comparator display only) and `irreversible_actions` (negotiation REJECT gate) —
two intentionally separate lists, not a duplication (different consumers, different tolerance for false positives).

**Shape of the system**: a pure in-memory, single-request regex + dict pipeline. No database, no network
I/O on the hot path, no shared mutable state across requests (after fix #2 below). "Scalability" here is
about the maintainability of the ruleset as more languages/verbs/dimensions are added — not runtime
throughput, which is a non-issue at this scope.

## 2. Findings and what was done about each

### Fixed today (low-risk, mechanically verified, committed in `d2d841f`)

1. **Dead code** — `aixl/translators/aixl_to_semantic.py` and `semantic_to_aixl.py` were 1-line
   re-export shims into `aixl.serialization.aixl_codec`, with **zero references** anywhere in the
   codebase or docs (confirmed by grep before deleting). Removed.

2. **Module-level mutable-global cache anti-pattern** — `natural_to_semantic.py` used a hand-rolled
   `global ALL_ACTION_RX: ... if ALL_ACTION_RX is None: ALL_ACTION_RX = [...]` lazy cache. Replaced with
   `@functools.lru_cache(maxsize=1)` on `_all_action_rx()`: identical compute-once-then-reuse semantics,
   no mutable global, thread-safe by construction.

   **Verification for both**: full suite 154/154 (unchanged from the 154/154 baseline before touching
   anything), and both real benchmarks re-measured and unchanged — `negotiation_eval.py` 19/21,
   `autonomous_negotiation_eval.py` 19/21, byte-for-byte the same numbers as before the refactor.

### Real, but deliberately NOT touched — reported as strategy, not executed

3. **Duplicated verb vocabulary**: `legacy02/translators/natural_to_semantic.py`'s `ACTION_RX` (0.2 base)
   and `core/normalizer.py`'s `EXTRA_ACTION_RX` (0.3 extension) are two separate tables, concatenated by
   hand in `_all_action_rx()` and again in `SemanticNormalizer.normalize_action()`. This is not a
   hypothetical smell — **this exact session** had to edit both tables to teach the translator a single
   new verb during the `irreversible_actions` evidence work earlier today.

   Why not merged now: the translator's action-matching is demonstrably **order-dependent** — a
   "tie-break rule" was a real, separately-shipped fix (E-INTEROP, see `BENCHMARK.md` §10) to a real
   cross-vendor accuracy regression caused by match order. Merging the two tables risks silently
   reordering matches and shifting the frozen accuracy numbers this project reports (72–96% across many
   rounds), which is exactly the kind of drift this project's own methodology exists to catch.

   **Safe path, if done**: merge into one ordered table in a new `aixl/core/action_vocab.py`, preserving
   the current concatenation order exactly (legacy first, then extensions — matching today's behavior
   bit-for-bit), then re-run not just the negotiation benchmarks but the translator accuracy scripts too,
   in a dedicated session isolated from any other change.

4. **Deliberate duplication**: `negotiation.py`'s `negotiate()` vs `autonomous_negotiation.py`'s
   `negotiate_autonomous_async()` share a near-identical ~40-line round-loop (REQUEST → loop{compare,
   CLARIFY, irreversible-action check, fetch sender value, ANSWER} → ACCEPT/REJECT) — one sync+local,
   one async+remote-MCP.

   I sketched a merge (a shared async core parameterized by a `get_answer` callback, with `negotiate()`
   wrapping it via `asyncio.run()`) and stopped when I found a concrete risk: the real `aixl_negotiate`
   MCP tool is a **sync** tool handler that calls `negotiate()` directly from inside the `mcp` SDK's own
   async dispatch loop. If that SDK calls sync tool handlers directly on its event-loop thread (rather
   than via a thread/executor — I did not verify which), `negotiate()` internally calling `asyncio.run()`
   would raise `RuntimeError: cannot be called from a running event loop` and break the tool that all
   three independent vendor clients (Claude Desktop, ChatGPT/Codex, Antigravity) already validated.

   **Safe path, if done**: `test_mcp_integration.py` already has a real-stdio test for `aixl_negotiate`;
   attempt the merge on a throwaway branch and run exactly that test first — green means the dispatch
   model is safe, red means keep the two files. Not worth the downside for a maintainability-only change
   without that check.

5. **`to_graph()` size**: ~450 lines, many sequential regex stages, several already delimited by their
   own comment headers (output format, visibility, "without X" constraint, date ranges). The single
   highest-friction file to extend safely. Recommended, not executed: extract the clearly-bounded,
   low-interdependency stages into named private helpers via pure code motion (same locals in, same
   locals out, same call order) — left as a follow-up given the volume of already-completed work today,
   since each extraction needs the same translator-accuracy-script re-verification as #3.

## 3. What was checked and found clean

`aixl/adapters/protocol_adapter.py` (ABC + small adapter classes), `aixl/core/comparator.py`,
`aixl/core/ambiguity.py`, `aixl/core/semantic_graph.py`, `lab/render.py`, `lab/server.py` — all
single-responsibility, no duplicated logic beyond what's listed above, no dead code found.

## 4. Net result

- 2 dead files removed, 1 mutable-global anti-pattern fixed — both committed, both verified with **zero
  behavioral drift** (154/154 tests; 19/21 + 19/21 benchmarks identical to pre-refactor).
- 3 further real, evidenced opportunities documented above with a concrete risk each and a safe
  verification path — deliberately left untouched today, per the explicit instruction to improve
  quality/maintainability without changing functionality, where "safe" could not yet be proven to the
  same standard as the two changes actually made.
