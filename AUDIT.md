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

### Fixed today (low-risk, mechanically verified)

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

3. **Duplicated verb vocabulary** — **partially done** (commit `6831314`). `legacy02/translators/natural_to_semantic.py`'s
   `ACTION_RX` (0.2 base) and `core/normalizer.py`'s `EXTRA_ACTION_RX` (0.3 extension) were being
   concatenated by hand, identically, in 5 separate call sites (`_all_action_rx()`, 3 places in
   `ambiguity.py`, `SemanticNormalizer.normalize_action()`) — silently omitting `+ EXTRA_ACTION_RX` at a
   new call site would drop the 0.3 verbs with no error. Fixed the part that was safe to fix: added one
   canonical `ALL_ACTION_RX = legacy.ACTION_RX + EXTRA_ACTION_RX` constant in `core/normalizer.py`
   (order preserved exactly — legacy first, then extensions, matching every prior call site's behavior
   bit-for-bit) and pointed all 5 call sites at it instead of recomputing the concatenation.

   **Deliberately NOT done**: actually moving the two tables' *content* into one file/table. The
   action-detection block in `to_graph()` (`pos`/`forbidden`/`allowed` construction, the E-INTEROP
   tie-break) uses `legacy.ACTION_RX` and `EXTRA_ACTION_RX` **asymmetrically** — `legacy.ACTION_RX` feeds
   a plain scan, `EXTRA_ACTION_RX` feeds `_scan()` with an article-exclusion filter — a real behavioral
   distinction at that one call site, not duplication, and merging the tables themselves (not just the
   concatenation) would risk touching it. Left exactly as-is, per the original risk assessment: the
   translator's action-matching is demonstrably **order-dependent** (the E-INTEROP tie-break rule,
   `BENCHMARK.md` §10, was a real fix for a match-order regression), so any change to the two tables'
   actual content still needs the same isolated-session, full-benchmark-re-run treatment this finding
   originally called for.

   **Verification for what WAS done**: full suite 154/154; rule-based translator accuracy on all 4 frozen
   blind sets identical byte-for-byte (tp/fp/fn/tn) to the pre-merge commit; both negotiation benchmarks
   unchanged (19/21, 19/21).

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

5. **`to_graph()` size** — **done** (commit `70c6e5a`). Extracted the 14 clearly-bounded,
   low-interdependency post-action-detection stages (output format, visibility, "without X" constraint,
   date ranges, quantities/selection, aggregate qualifiers, name/numeric references, structured
   conditions, intent/goal derivation, step order, forbidden/allowed application) into named private
   helpers via pure code motion — same locals in, same locals out, same call order, nothing reordered.
   Deliberately left the action-detection block (pos/forbidden/allowed construction, the E-INTEROP
   tie-break) untouched in place, exactly as flagged above — highest transcription risk, not worth it
   for a maintainability-only change.
   **Verification, not just tests**: full suite 154/154; rule-based translator accuracy on all 4 frozen
   blind sets (`blind_eval` rounds 1-4) — compared via `git stash` against the pre-refactor commit —
   tp/fp/fn/tn identical, byte-for-byte, in every round; both negotiation benchmarks unchanged (19/21,
   19/21). Zero behavioral drift on the exact numbers this project reports as evidence.

## 3. What was checked and found clean

`aixl/adapters/protocol_adapter.py` (ABC + small adapter classes), `aixl/core/comparator.py`,
`aixl/core/ambiguity.py`, `aixl/core/semantic_graph.py`, `lab/render.py`, `lab/server.py` — all
single-responsibility, no duplicated logic beyond what's listed above, no dead code found.

## 4. Net result

- 2 dead files removed, 1 mutable-global anti-pattern fixed, and `to_graph()`'s 14 safely-separable
  stages extracted into named functions — all committed, all verified with **zero behavioral drift**
  (154/154 tests; rule-based translator accuracy identical byte-for-byte on all 4 frozen blind sets;
  19/21 + 19/21 negotiation benchmarks unchanged).
- Finding #3 partially closed: the duplicated *concatenation* of the two verb tables (5 call sites) is
  now a single `ALL_ACTION_RX` constant — verified with the same zero-drift standard (154/154 tests,
  byte-for-byte blind-set accuracy, unchanged negotiation benchmarks). The two tables' *content* stays
  split (0.2 vendored base vs 0.3 extensions) and the action-detection block's asymmetric use of them
  stays untouched — merging the content itself remains a separate, still-open, higher-risk item.
- 1 further real, evidenced opportunity documented above with a concrete risk and a safe verification
  path — deliberately left untouched: the negotiate()/negotiate_autonomous_async() round-loop
  duplication (#4).
