# Phase log (master prompt §3/§48)
Each phase: IMPLEMENTED · TESTED · RESULT · KNOWN ISSUES · NEXT STEP.

| Phase | Implemented | Tested | Result | Known issues | Next |
|---|---|---|---|---|---|
| 1 architecture | package layout, pyproject, vendored 0.2 analyzer (`legacy02`), venv with pytest+tiktoken | import smoke | ARCHITECTURE.md | none | objects |
| 2 semantic objects | SemanticObject, SemanticRelation, SemanticGraph, canonical(), JSON | tests/test_objects.py (7) | pass | flat frame (no per-action targets) | ontology |
| 3 ontology | ACTION/ENTITY/DATA/TIME/MODIFIER, antonyms, configurable weights/severity | test_objects | pass | TIME severity is an ASSUMPTION | normalizer |
| 4 normalizer | closed lexicons: verbs, units, aggregates, formats, numbers, times | tests/test_normalizer.py (5) | pass | no fuzzy matching by design | translator |
| 5 translator | ES/EN/PT rule-based text→graph (+ extensions) | tests/test_translator.py (11) | pass on dev; **blind sets 76–80 %** | long-tail vocabulary | codec |
| 6 AIXL codec | graph↔AIXL 0.3, JSON codec | tests/test_codec.py (17) | roundtrip 100 % | AIXL longer than text | comparator |
| 7 comparator | layered canonical comparison, severity, similarity, SEMANTIC DIFF | tests/test_equivalence.py (13) | pass | similarity is experimental | drift |
| 8 drift | levels from worst severity, CRITICAL_SEMANTIC_DRIFT | tests/test_drift.py (5) | pass; S2 92–97 % rule-based, 97 % LLM route | TIME=MAJOR assumption | ambiguity |
| 9 ambiguity | heuristic detector with reasons/fields/confidence | tests/test_ambiguity.py (8) | 90 % on blind items (first run) | heuristic pronoun resolution | contradiction |
| 10 contradiction | explicit opposition on same object | tests/test_contradiction.py (6) | 75 % on blind items (first run) | no implicit contradictions | tests |
| 11 tests | 99 pytest tests incl. 19 regression bug classes | `pytest` | 99 passed | | benchmark |
| 12 benchmark | dev200, 4 blind sets, LLM-route evaluator, compression (tiktoken) | run | see BENCHMARK.md | S1 not met by rule-based | lab |
| 13 Semantic Lab | CLI lab, stdlib web app (`python cli.py serve`), 6 demos | tests/test_demos.py (8); web app verified in a browser | works | | audit |
| 14 audit | see README §Audit | | | | 0.4 roadmap |
| 15 fingerprint (2026-10-02, master prompt §40) | `aixl/core/fingerprint.py`, `semantic_fingerprint(_aixl)` | tests/test_fingerprint.py (8); agrees with comparator on 130/130 dev-set pairs (EQ/NEG/QTY/DATE/DIFF) | pass; 202 tests total | hash = SHA-256[:16] of `canonical()`; relative TIME tokens depend on `today` (pass it for cross-day stability); inherits translator limits (long-tail vocabulary) | benchmark 5×100 (§42) |
| 16 benchmark 5×100 (2026-10-02, §42) | `benchmarks/sil5x100_{gen,eval}.py`, `data/sil5x100/`, BENCHMARK.md section | tests/test_sil5x100.py (ratchet, 7 tests); 209 total | v1.1: 470/500 = 94.0 % (EQ 100, NOT 97, PART 100, AMBIG 82, CONTRA 91); 0 ambiguity FPs | PT gaps (ambiguity + contradiction lexicons), silent drop of unknown nouns (§66) | fix PT lexicons; unknown-noun warning |
| 17 benchmark v1.2 fixes (2026-10-02) | PT lexicons (ambiguity/enable/after) + `core/lexicon_gaps.py` UNRECOGNIZED_TERMS warning | 211 tests; 5×100 = 497/500 = 99.4 %; PT 67/67; invoice-class 62/62 warned; blind round 1 unchanged | pass | warning noise 7.3 % of texts; verdict on unknown-noun swaps still PARTIAL (reported, not fixed) | B: adversarial security suite (§39) |
| 18 adversarial security suite (2026-10-02, §39) | `sil_security_{gen,eval}.py`, `sanitize_input`, SCOPE constraint, `email` verb, directional context severity, NO_ACTION_RECOGNIZED | tests/test_sil_security.py (18); 229 total; blind r1–r4 identical before/after | combinatorial 450/450 flagged, all expected-critical critical; HARD 57/57 flagged, 54/57 critical; 0/31 false alarms | context_poisoning not covered; period-swap and GIVE-access limitations; same-author | docs §50 |
| 19 documentation §50 (2026-10-02) | `docs/` (11 documents), CLI `encode/decode/validate/fingerprint`, `tests/test_docs.py` (24) | 253 tests; docs verified: every `aixl-example` line vs the encoder, every CLI command/API function named, exit codes, version policy, the extension worked example runs | pass | no REST API, no extension registry, no capability handshake (documented as design-only); relative dates are date-anchored in the AIXL line (documented deviation from §16) | independent review of the docs by a non-author |
