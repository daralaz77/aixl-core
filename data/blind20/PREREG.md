# blind20 (80 pairs) — pre-registration, written 2026-11-03 BEFORE the pairs exist
Purpose: a fresh test of the rule comparator (`compare_texts`) after the fixes that followed blind19 (commit 5171c4b). blind19 failed G2 (NOT_EQUIVALENT precision 13/21) and is SPENT; its fixes were written knowing its failures, so blind19 cannot show whether they generalise.
Family list is DIFFERENT on purpose: only 2 families repeat (tag questions and antonym swaps, the earlier fixes); 8 families were never used to tune anything: modal_strength, only_focus_scope, sequence_and_time, recipient_and_or_coordination,
numeric_forms_units, verb_paraphrase_lexical, conditional_necessary_sufficient, negation_scope_adverbs (hardly / never / no longer / not yet).
Code frozen by hash in CODE_FREEZE.json (same files as blind19, now at commit 5171c4b). Authors: two NEW agents of other models than blind19's (Fable and Haiku; blind19 used Opus and Sonnet), 40 pairs each, no tools, nothing about AIXL, its code or its results;
only the family list, the label definitions and the schema. 4 pairs per family per author, about 40 / 40 / 20 EQUIVALENT / NOT_EQUIVALENT / UNDECIDABLE, es / en / pt mixed.
Scope: the SEMANTIC comparator alone (rule-based, offline). No arbiter or hybrid claim.
Gates (written beforehand), unchanged from blind19 so the two sets are comparable:
  G1 false-EQUIVALENT <= 3% of the non-EQUIVALENT-labelled pairs (UNDECIDABLE included), every id listed.
  G2 NOT_EQUIVALENT precision >= 90% of the pairs the semantic calls NOT_EQUIVALENT.
  G3 reported only: proven-EQUIVALENT recall, NOT_EQUIVALENT recall, INCONCLUSIVE rate.
  G4 per-family table of false-EQUIVALENT and wrong NOT_EQUIVALENT.
Claim policy: "the rule comparator generalises to text by other authors" may be stated ONLY IF G1 and G2 both pass. A pass on blind20 alone would still rest on two authors and 80 pairs; the claim would be worded that narrowly.
Labels are the authors' and are NOT corrected after the run; disputed labels are listed with both readings, gates use the original labels. One run, on frozen code; the evaluator refuses a second run and refuses if code or pair files changed.
Expectation written beforehand: G1 will hold again (fail-closed design). G2 is uncertain: the 8 new families probe constructions the comparator has hardly been tuned on, so new over-confident definite differences are likely; if G2 fails again the finding is
"definite NOT_EQUIVALENT is not yet reliable outside the tuned constructions", not an excuse to relabel.
Amendment 2026-11-03, still BEFORE any pair exists: the Fable author failed with an API credit error (HTTP 429) and produced nothing. Its 40 pairs (ids C001-C040) are written instead by a fresh Opus instance given the identical prompt.
So blind20 authors are Haiku (new model) and a fresh Opus instance (same model as one blind19 author, but a new instance and a different family list). This weakens the "other authors" claim: it must be worded as "new instances with a partly new model mix".
Honest limits written beforehand: two model authors; Haiku may write noisier labels, which would depress G2 through label error, so wrong NOT_EQUIVALENT will be read pair by pair and split into comparator defects vs disputed labels, but the gate stays on original labels;
80 pairs give a wide interval.

## RESULT (run once on the FROZEN code at 5171c4b, 2026-11-03; raw output RESULT_run1.txt) — set is now SPENT
Pairs: Opus C001-C040 + Haiku D001-D040 = 80 (31 EQUIVALENT, 34 NOT_EQUIVALENT, 15 UNDECIDABLE). Verdicts: 53 INCONCLUSIVE, 19 NOT_EQUIVALENT, 8 EQUIVALENT.
| gate | result | verdict |
|---|---|---|
| G1 false-EQUIVALENT <= 3% of non-EQUIVALENT-labelled | **4/49 = 8.2%** (C012, C028, D027, D036) | **FAIL** |
| G2 NOT_EQUIVALENT precision >= 90% | **11/19 = 57.9%** | **FAIL** |
| G3 (report only) | proven-EQUIVALENT recall 4/31 = 12.9%; NOT_EQUIVALENT recall 11/34 = 32.4%; INCONCLUSIVE 53/80 = 66.2% | — |
**Claim policy outcome: "the rule comparator generalises to text by other authors" is NOT allowed.** Both gates fail on constructions the comparator had not been tuned on. The "0 false-EQUIVALENT" seen on blind19 does NOT hold here.
Reading of the 4 false-EQUIVALENT (labels NOT corrected). C012 is a REAL SAFETY DEFECT: 'No es necesario que entregues X' (not obligatory) vs 'Es necesario que no entregues X' (obligatory NOT to) is proven EQUIVALENT; the label NOT_EQUIVALENT is right.
C028 and D027 ('2.500' vs '2,500', '1.000' vs '1,000'): the thousands/decimal separator is not modelled and both texts compare equal; the authors' UNDECIDABLE is the defensible reading, so the comparator should have stayed INCONCLUSIVE (real defect: false confidence).
D036 ('whenever' vs 'if'): author UNDECIDABLE; the comparator drops 'whenever' (disputed label, but a generic-vs-single-event condition is a real distinction that should keep it INCONCLUSIVE).
Reading of the 8 wrong NOT_EQUIVALENT. Comparator defects: C025 ('1.500' vs 'mil quinientas': the spelled number is parsed as 1000 + 500, label EQUIVALENT is right); D034 ('solo ... si' vs '... únicamente si': 'únicamente' is not recognised as 'solo', so necessary vs sufficient is asserted wrongly; label EQUIVALENT right);
D029 ('archive' vs 'move to the archive': an extra verb word is anchored as an item addition); C019 and C021 (scope-of-'before' and 'either' grouping: the authors call them UNDECIDABLE and the comparator should stay INCONCLUSIVE).
Disputed labels (both readings): C004 (negative question vs tag), C035 ('se' vs 'somente se', same necessary/sufficient dispute as blind19 B024), D031 (revisar vs validar). Excluding these three, precision would still be 11/16 = 68.8%.
Family table: no family is clean; the failures concentrate in numeric_forms_units (2 false-EQUIV + 1 wrong NOT_EQUIV) and conditional_necessary_sufficient. Tag questions and antonym swaps (the two families that repeat from blind19) had 0 false-EQUIV, 1 wrong NOT_EQUIV (C004, disputed) and 0 respectively.
Limits: two model authors, one of them (Opus) also wrote part of blind19, 80 pairs, author labels, a wide interval. Nothing in the code was changed during the run.
## AFTER the run (code changed; the evaluator now refuses to re-run) — development evidence only
Defects fixed with tests on OWN sentences (tests/test_semantic_r.py): (1) 'no es necesario / não é necessário / it is not necessary / no es obligatorio' -> NOT_REQUIRED (it was parsed as a prohibition, so 'not necessary that you X' and 'necessary that you do not X' were proven EQUIVALENT; the double-negation case is flagged);
(2) '4.200' vs '4,200' (single separator + exactly three digits) raises AMBIGUOUS_NUMBER_SEPARATOR, never proven equal; (3) a spelled compound number ('mil quinientas', 'dos mil') raises UNREPRESENTABLE_COMPOUND_NUMBER and suppresses definite quantity diffs;
(4) 'whenever / siempre que / sempre que / cada vez que / every time' raises UNREPRESENTABLE_WHENEVER, never the same as a plain 'if'; (5) an 'only' focus on the verb in one text vs a necessary condition in the other is INCONCLUSIVE; (6) 'either / neither / both' is a grouping marker, not an added item;
(7) the action word reappearing as a noun on the other side is not an added item; (8) the same time modifier attached to a different step in each text is INCONCLUSIVE; (9) an unmodelled modal adjective (possible / optional ...) present on ONE side only suppresses definite diffs.
Post-hoc on the same 80 pairs (NOT a result: the set is spent and the fixes were written knowing the failures): false-EQUIVALENT 0/49 (was 4), NOT_EQUIVALENT precision 12/15 (was 11/19), and the 3 remaining wrong are exactly the 3 disputed labels (C004, C035, D031); proven-EQUIVALENT recall unchanged at 4/31.
blind19 post-hoc: 0/48 false-EQUIVALENT, precision 14/17. SemAntoNeg unchanged (0 false-EQUIVALENT, 2970 NOT_EQUIVALENT, 8 wrong). Full suite 1564 passed. Two sets in a row failed the same gate for different reasons: any new claim needs blind21 written by authors who have seen none of this.
