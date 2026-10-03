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

4. **Deliberate duplication** — **done** (commit `33497a6`). `negotiation.py`'s `negotiate()` vs
   `autonomous_negotiation.py`'s `negotiate_autonomous_async()` shared a near-identical ~40-line
   round-loop (REQUEST → loop{compare, CLARIFY, fetch sender value, empty-check, irreversible-action
   check, ANSWER} → ACCEPT/REJECT) — one sync+local, one async+remote-MCP.

   The risk flagged above was resolved, not assumed: read the `mcp` SDK's own source
   (`mcp.server.mcpserver.utilities.func_metadata.FuncMetadata.call_fn`) and confirmed a sync tool
   handler runs via `anyio.to_thread.run_sync` — a genuine worker thread with no event loop of its own —
   so `negotiate()` calling `asyncio.run()` internally is safe from `aixl_negotiate`'s sync MCP handler.
   Extracted the shared control flow into `_negotiate_core()` (async, in `negotiation.py`), parameterized
   by `get_request()`/`get_answer(dim, belief)` — the only real difference between the two callers is
   where the sender's data comes from.

   **A real behavioral difference surfaced during the merge, not shipped blind**: an initial version
   assumed the empty-sender-value REJECT and the irreversible-action REJECT were mutually exclusive
   (reasoning that d.source can't be both empty and irreversible) — true, but incomplete: d.target (the
   *receiver's* own candidate) can independently be irreversible regardless of the sender's value. The
   existing "Quita el ticket #77." test caught this immediately (wrong REJECT *reason* text, same
   `converged=False`). Fixed by restoring `negotiate()`'s original check order exactly for both callers,
   at the cost of the autonomous path no longer saving one round-trip in that specific reject case —
   correctness over a micro-optimization.

   **Verification**: full suite 154/154, including the real-subprocess MCP integration tests for both
   tools; translator accuracy unaffected (this change never touches the translator); both negotiation
   benchmarks unchanged (19/21, 19/21); a real CLI run (`cli.py negotiate "Close ticket #77." "Delete
   ticket #77."`) still REJECTs with the identical reason.

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

## 2b. Bug found by CI itself (2026-09-30, after this audit shipped)

Adding GitHub Actions CI (`.github/workflows/tests.yml`, matrix Python 3.11/3.12) immediately caught a
real cross-version bug this audit's own local verification could never have found: local dev always ran
on Python 3.14, where `f"...{re.match(r'...\\\\...', v)...}"` (a raw regex with backslashes written
directly inside an f-string expression, `aixl/legacy02/core/encoder.py:29`) silently worked — that
syntax is only valid from Python 3.12 on (PEP 701). On the project's own declared floor
(`requires-python >= 3.11`), it's a `SyntaxError` that fails to even import the package. Fixed by
precompiling the pattern as a module-level constant (`_BARE_SCALAR`) instead of embedding regex syntax
in the f-string. Confirmed it was the only instance in the repo (grepped, then AST-walked every
`FormattedValue` node for a literal backslash — zero other hits) and re-verified the full zero-drift
standard on a REAL Python 3.11.16 (installed via Homebrew, this machine only had 3.14): 154/154 tests,
translator accuracy identical on all 4 frozen blind sets, both negotiation benchmarks unchanged.

This is the clearest argument for the CI this audit didn't originally include: every "zero behavioral
drift" verification in this document was run only on whatever Python this machine happened to have —
CI now runs it against the project's actual declared support range on every push.

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
- Finding #4 closed: the negotiate()/negotiate_autonomous_async() round-loop is now one function
  (`_negotiate_core`), not two — the risk that blocked it was investigated and resolved (not assumed)
  by reading the `mcp` SDK's own dispatch code, and a real behavioral difference the merge surfaced was
  caught by the existing test suite and fixed before shipping, not missed.

All 5 original audit findings are now resolved: 2 fixed outright, 2 merged after their flagged risks
were actually investigated (one turned out safe, one needed a genuine fix), and 1 (the verb tables'
*content*, as opposed to their concatenation) remains deliberately split, since merging it still needs
the isolated-session, full-benchmark treatment described in finding #3 above.

## Addendum 2026-10-03 — what this audit did and did not cover
This audit (2026-09-30) is a **code-structure** audit: data flow, duplication, dead code, scalability of the ruleset. Its findings and verifications stand as written, with these updates:
* The data-flow diagram in §1 is dated: `A2AAdapter` was a stub when the diagram was drawn and became real the same day (E-A2A); `core/lexicon_gaps.py`, `core/completeness.py`, `core/fingerprint.py`, the `R:` residue atom and the `residue` canonical dimension were added afterwards (see [ARCHITECTURE.md](ARCHITECTURE.md)). Suite size is now 462 tests (154 at the time).
* "Zero behavioral drift" was verified against the frozen blind sets 1–4 and the negotiation benchmarks, i.e. against **the project's own vocabulary family**. It says nothing about open-domain correctness.
* **What the audit did not look for, and later experiments found to be the dominant risk**: not code structure but *semantic coverage*. On text written by other authors the closed vocabulary silently drops whatever has no slot, so 40–59 % of non-equivalent pairs were judged equivalent (blind10/blind11; [docs/EVIDENCE.md](docs/EVIDENCE.md)). No refactor of the kind listed above could have exposed that; only benchmarks by authors outside the project did. Any future audit should include an out-of-vocabulary, other-author evaluation as a first-class item.
* Process note: a commit of 2026-10-03 (`blind12 … frozen`) accidentally included two WIP files of a parallel `distill/` workstream because of a blanket `git add -A`; commits since then stage explicit paths only.
