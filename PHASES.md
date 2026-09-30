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
