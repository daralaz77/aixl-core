# blind19 (80 pairs) — pre-registration, written 2026-11-03 BEFORE the pairs exist
Purpose: first fresh evidence on the rule comparator (`compare_texts`) AFTER three post-blind18 changes, none of which has ever been measured on text written by other authors:
(a) English tag questions stripped + AMBIGUOUS_TAG_QUESTION (commit ff9203f); (b) Spanish/Portuguese confirmation tags (152b228); (c) antonym lexicon, one known adjective swap in a polarity-free pair -> NOT_EQUIVALENT (0377588).
These were developed against SemAntoNeg and the author's own probes, so SemAntoNeg and those probes are development data, NOT evidence. blind14-18 are void for re-runs (their CODE_FREEZE includes parser.py).
Code frozen by hash in CODE_FREEZE.json (parser, comparator, lexicon, model, hybrid, arbiter, rules). Authors: two fresh agents (Opus, Sonnet), 40 pairs each, no tools, nothing about AIXL, nothing about its code or results,
only the family list, the label definitions and the JSONL schema. Families (4 pairs per family per author when possible): tag_question_confirmation (es/pt/en), antonym_swap, negation_vs_antonym, double_negation_modal,
quantifier_negation_scope, condition_polarity (unless / only if / if not), quantity_relations (at least / at most / more than / fewer than), time_relations (before / after / until / by), exception_vs_inclusion,
true_paraphrase_distractor (wording differs, meaning identical — measures recall). Labels: EQUIVALENT / NOT_EQUIVALENT / UNDECIDABLE (the construction is genuinely ambiguous). Target mix about 40 / 40 / 20.
Scope: the SEMANTIC comparator alone (rule-based, offline). The 2-of-2 arbiter judges are NOT run in this set; no claim about the hybrid or the arbiter is made from it.
Gates (written beforehand), over the pairs whose label is not EQUIVALENT (UNDECIDABLE included) and over all pairs:
  G1 false-EQUIVALENT (semantic says EQUIVALENT, label is not EQUIVALENT) <= 3% of non-EQUIVALENT-labelled pairs, and the count is reported with every id.
  G2 NOT_EQUIVALENT precision (semantic says NOT_EQUIVALENT and label is NOT_EQUIVALENT) >= 90% of the pairs the semantic calls NOT_EQUIVALENT.
  G3 reported only, no threshold: proven-EQUIVALENT recall on EQUIVALENT-labelled pairs; INCONCLUSIVE rate; NOT_EQUIVALENT recall.
  G4 per-family table of false-EQUIVALENT and wrong NOT_EQUIVALENT, so a failure is attributed to a construction and not averaged away.
Claim policy: "the rule comparator generalises to text by other authors" may be stated ONLY IF G1 and G2 both pass; failing either keeps the claim "not shown". Labels are the authors' and are NOT corrected after the run;
disputed labels are listed in the report with both readings, and the gates are computed on the original labels only.
Run once on the frozen code. After the run the evaluator must refuse to re-run if the code or the pair files changed (same hash discipline as blind13-18). Any later fix is development evidence only.
Expectation written beforehand: G1 may hold (the comparator is fail-closed); G2 is the risk (over-confident definite diffs, e.g. when authors read a pair as UNDECIDABLE); recall will be low because most wording variants stay INCONCLUSIVE.
Honest limits written beforehand: two model authors, one per vendor family they share with the judges used elsewhere; 80 pairs give a wide interval (a 3% gate is 1 false pair in ~48 non-equivalent); labels come from authors, not humans.

## RESULT (run once on the FROZEN code, 2026-11-03; raw output RESULT_run1.txt) — set is now SPENT
Pairs: Opus A001-A040 + Sonnet B001-B040 = 80 (32 EQUIVALENT, 33 NOT_EQUIVALENT, 15 UNDECIDABLE). Verdicts: 54 INCONCLUSIVE, 21 NOT_EQUIVALENT, 5 EQUIVALENT.
| gate | result | verdict |
|---|---|---|
| G1 false-EQUIVALENT <= 3% of non-EQUIVALENT-labelled | **0/48 = 0.0%** | PASS |
| G2 NOT_EQUIVALENT precision >= 90% | **13/21 = 61.9%** | **FAIL** |
| G3 (report only) | proven-EQUIVALENT recall 5/32 = 15.6%; NOT_EQUIVALENT recall 13/33 = 39.4%; INCONCLUSIVE 54/80 = 67.5% | — |
**Claim policy outcome: "the rule comparator generalises to text by other authors" is NOT allowed** (G1 holds, G2 fails). What the data DO support: no silent equivalence on this set; the comparator over-asserts definite differences.
Reading of the 8 wrong NOT_EQUIVALENT (labels NOT corrected; gates use the original labels). Disputed labels, both readings: B004 (author UNDECIDABLE; main clauses 'No vienes' vs 'Vienes' really differ), B024 ('only if' vs 'if': necessary vs sufficient is
the logical reading, the author took the pragmatic one), B036 (exactly-12 boundary: arguably should stay INCONCLUSIVE). Even if all three were excluded, precision would be 13/18 = 72%, still below the gate.
Real defects found (development evidence only from now on): (1) 'no está prohibido / não é proibido X' vs 'está permitido X' parsed as DONT vs MAY: A013, B015; (2) 'não é permitido sem X' vs 'é obrigatório X' reported as an ITEMS addition on
unmodelled modal words: A015; (3) discrete counts 'como mínimo tres' vs 'más de dos' compared as at_least 3 vs greater_than 2 with no integer reasoning: B025; (4) 'last' vs 'final' not unified, so a reference difference was asserted: B038.
Family table: 0 false-EQUIVALENT in every family; wrong NOT_EQUIVALENT concentrated in double_negation_modal (3 of 8 pairs). None of the antonym lexicon or the tag-question changes caused a false-EQUIVALENT; B004 shows the tag change makes the main clause decide.
Limits: two model authors, 80 pairs, author labels, a wide interval on both gates. Nothing in the code was changed during the run.
## AFTER the run (code changed; the evaluator now refuses to re-run) — development evidence only
Four defects fixed with tests that use OWN sentences (tests/test_semantic_r.py): (1) 'no está prohibido / not forbidden' -> MAY, only when the negation precedes the prohibition word; (2) a modal adjective (obligatorio / required / possible ...)
present only on one side can no longer create an ITEMS addition/loss; (3) at-least-n vs more-than-(n-1) (and at-most-n vs fewer-than-(n+1)) is INCONCLUSIVE, the off-by-one in the other direction stays NOT_EQUIVALENT; (4) 'final' (an ordinal-like word, also inside a
time clause) and a temporal conjunction heading extra words no longer give a definite reference/items difference. Full suite 1551 passed. Post-hoc on the same 80 pairs (NOT a result, the set is spent and the fixes were written knowing the failures):
false-EQUIVALENT still 0/48, NOT_EQUIVALENT precision 13/16, the 3 remaining wrong are exactly the 3 disputed labels (B004, B024, B036), proven-EQUIVALENT 7/32. SemAntoNeg unchanged (0 false-EQUIVALENT, 2970 NOT_EQUIVALENT).
