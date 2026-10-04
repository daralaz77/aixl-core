# blind18 (SHORT, 70 pairs) — pre-registration, written 2026-10-03 BEFORE the pairs exist
Purpose: test the AMBIGUITY VETO added to the hybrid after blind17: arbiter SAME + semantic INCONCLUSIVE with an AMBIGUOUS_* flag -> REVIEW. The rule was designed after seeing blind17's X024, so blind17 is development data for it.
Code + arbiter rules frozen by hash in CODE_FREEZE.json. Authors: two fresh agents (Opus, Sonnet), 35 pairs each, no tools, nothing about AIXL, ambiguity-focused families. Judges: two fresh agents (Sonnet, Haiku),
rules_v1.txt + (id, a, b) only, shuffled, no labels/families/semantic output; the exact TSV format is required and ONE retry is allowed for an invalid answer (logged in JUDGE_LOG.md).
Dev-set calibration of the rule (written beforehand): over the 696 development pairs, 38 INCONCLUSIVE pairs carry an AMBIGUOUS flag: 29 truly not-equivalent/undecidable, 9 equivalent (cost ~3.3% of true equivalents).
Gates (written beforehand):
  R1 hybrid false-SAME <= 5% of non-EQUIVALENT-labelled pairs (UNDECIDABLE included) AND <= the arbiter-alone false-SAME count (the rule must not hurt).
  R2 hybrid SAME on >= 85% of EQUIVALENT-labelled pairs.
  R3 of the pairs the AMBIGUITY rule sends to REVIEW, >= 60% are labelled not-equivalent/undecidable.
Claim policy: "the hybrid is safer than the arbiter alone" may be stated ONLY IF the arbiter alone made >= 1 false-SAME that the rule turned into REVIEW (benefit > 0) AND R1-R3 hold. Otherwise the claim stays "no evidence of added protection".
Expectation written beforehand: the arbiter alone will make several false-SAMEs on this ambiguity-heavy set (double negations under modals, 'no todos', and/or grouping); R2 may drop a little because some true paraphrases carry an ambiguity flag.

## RESULT (run once on the FROZEN code + rules, 2026-10-03; raw output RESULT_run1.txt; judge protocol JUDGE_LOG.md) — set is now SPENT
Pairs: Opus X001-X035 + Sonnet Y001-Y035 = 70 (26 EQUIVALENT, 22 NOT_EQUIVALENT, 22 UNDECIDABLE; ambiguity-heavy by design). Judges Sonnet + Haiku: 70/70 valid each, no retry needed.
| gate | result | verdict |
|---|---|---|
| R1 hybrid false-SAME <= 5% and <= arbiter alone | hybrid **2/44 = 4.5%** vs arbiter alone **4/44 = 9.1%** | PASS |
| R2 hybrid SAME on >= 85% of equivalent | **21/26 = 80.8%** | **FAIL** |
| R3 >= 60% of ambiguity-rule REVIEWs truly not-equivalent/undecidable | **1/2 = 50%** (n = 2) | **FAIL** |
Benefit: 2 arbiter false-SAMEs turned into REVIEW (X021, Y022: conditional-scope pairs). Cost: 3 true SAMEs turned into REVIEW (X003, X010: wrong DEFINITIVE semantic NOT_EQUIVALENT; Y001: the ambiguity rule on a double negation).
**Claim policy outcome: "the hybrid is safer than the arbiter alone" is NOT allowed** (benefit > 0 and R1 hold, but R2 and R3 fail). The evaluator printed 'allowed: True' because it checked only benefit and R1; that line was wrong
relative to the pre-registered policy and has been corrected in benchmarks/blind18_eval.py (RESULT_run1.txt keeps the original output).
Semantic alone: false-equivalent 3/44 = 6.8% (X022, X024, Y002), NOT_EQUIVALENT precision 10/14 = 71%, recall 45%. Label inconsistency worth knowing: 'No es cierto que no debas X' vs 'Debes X' was labelled NOT_EQUIVALENT in blind17
(X024) and EQUIVALENT here (Y001; and X001 'No está permitido no registrar' vs 'Es obligatorio registrar'), i.e. authors disagree on exactly the construction the rule flags.
## AFTER the run (code changed; the evaluator now refuses to re-run) — development evidence only
Four real defects were traced and fixed with tests (tests/test_semantic_r.py): (a) double negation under a modal cancelled into 'permitted' (Y002, a safety false-equivalent); (b) 'and call' not split, so a trailing condition's
scope was not flagged (X022); (c) 'never fail to' vs 'always' gave a spurious TIME addition (X003); (d) 'not every' vs 'some … not' (X010). Post-hoc with the stored judge verdicts: blind18 hybrid false-SAME 1/44 vs arbiter 4/44,
SAME on equivalent still 21/26, REVIEW 6/70. Dev-set totals (7 sets, 766 pairs): NOT_EQUIVALENT precision 184/190, false-equivalent 2/464 (blind17 Y009, a disputed label; blind18 X024). 581 tests.
