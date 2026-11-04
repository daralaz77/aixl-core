# blind21 (80 pairs) — pre-registration, written 2026-11-04 BEFORE the pairs exist
Purpose: a fresh test of the rule comparator (`compare_texts`) after the fixes that followed blind19 and blind20 (commit 1c08035). blind19 and blind20 are SPENT and both failed G2 (blind20 also G1); their fixes were written knowing their failures, so neither can show whether the fixes generalise.
Families are ALL NEW: none of the 10 below was used in blind19 or blind20, and none was used to tune any rule: role_reversal (who does what to whom), passive_active_voice, frequency_adverbs (always / usually / sometimes / never),
universal_existential_quantifiers (all / some / none / not all), comparison_degree (more than / as ... as / less than / the most), causal_vs_temporal (because / so / after / then), restrictive_relative_clause (who / that / which scope),
approximation_exactness (about / exactly / roughly / up to), date_and_ordering_formats (dd/mm vs mm/dd, first / second, A before B), list_order_and_priority (in this order / first of all / priority).
Code frozen by hash in CODE_FREEZE.json (same files as blind20, now at commit 1c08035). Authors: two fresh agents (Fable and Sonnet; if one fails the replacement is recorded here before any pair exists), 40 pairs each, no tools, nothing about AIXL, its code or its results;
only the family list, the label definitions and the schema. 4 pairs per family per author, about 40 / 40 / 20 EQUIVALENT / NOT_EQUIVALENT / UNDECIDABLE, es / en / pt mixed.
Amendment 2026-11-04, still BEFORE any pair exists: the Fable author failed with an API credit error (HTTP 429, same as blind20) and produced nothing. Its 40 pairs (ids E001-E040) are written instead by a fresh Opus instance given the identical prompt. Authors are therefore Opus (fresh instance) and Sonnet (fresh instance); both models also wrote parts of blind19/20, but these are new instances with a new family list.
Scope: the SEMANTIC comparator alone (rule-based, offline). No arbiter or hybrid claim.
Gates (written beforehand), unchanged from blind19/20 so the three sets are comparable:
  G1 false-EQUIVALENT <= 3% of the non-EQUIVALENT-labelled pairs (UNDECIDABLE included), every id listed.
  G2 NOT_EQUIVALENT precision >= 90% of the pairs the semantic calls NOT_EQUIVALENT.
  G3 reported only: proven-EQUIVALENT recall, NOT_EQUIVALENT recall, INCONCLUSIVE rate.
  G4 per-family table of false-EQUIVALENT and wrong NOT_EQUIVALENT.
Claim policy: "the rule comparator generalises to text by other authors" may be stated ONLY IF G1 and G2 both pass, worded narrowly (new instances, 80 pairs, author labels).
Labels are the authors' and are NOT corrected after the run; disputed labels are listed with both readings, gates use the original labels. One run, on frozen code; the evaluator refuses a second run and refuses if code or pair files changed.
Expectation written beforehand: G1 may hold (fail-closed design) but blind20 showed it can fail on untuned constructions; G2 will probably fail again, because voice, role reversal and quantifier scope are constructions the comparator has never been tuned on.
If a gate fails the finding is "not yet reliable outside the tuned constructions", not an excuse to relabel.
Honest limits written beforehand: two model authors; labels come from models, not humans; 80 pairs give a wide interval; wrong NOT_EQUIVALENT will be read pair by pair into comparator defects vs disputed labels, but the gate stays on original labels.

## RESULT (run once on the FROZEN code at 1c08035, 2026-11-04; raw output RESULT_run1.txt) — set is now SPENT
Pairs: Opus E001-E040 + Sonnet F001-F040 = 80 (30 EQUIVALENT, 34 NOT_EQUIVALENT, 16 UNDECIDABLE). Verdicts: 65 INCONCLUSIVE, 11 NOT_EQUIVALENT, 4 EQUIVALENT.
| gate | result | verdict |
|---|---|---|
| G1 false-EQUIVALENT <= 3% | **4/50 = 8.0%** (E025, F026, F027, F028) | **FAIL** |
| G2 NOT_EQUIVALENT precision >= 90% | **6/11 = 54.5%** | **FAIL** |
| G3 (report only) | proven-EQUIVALENT recall 0/30; NOT_EQUIVALENT recall 6/34 = 17.6%; INCONCLUSIVE 65/80 = 81.2% | — |
Claim policy outcome: "the rule comparator generalises to text by other authors" is NOT allowed. Third set in a row to fail G2.
Note: a first attempt wrote an empty RESULT_run1.txt via shell redirection before the script started; the guard refused, no pair was evaluated, the file was deleted, and the run above is the only real one.
Reading (labels NOT corrected). False-EQUIVALENT: all 4 are one construction, restrictive vs non-restrictive relative clause (comma before who/que): the comma is ignored and the texts compare equal (E025, F026, F027 labelled NOT_EQUIVALENT; F028 UNDECIDABLE). Real defect, fail-open.
Wrong NOT_EQUIVALENT: F024 and E024/F022 = causal vs temporal ('since', 'after' vs 'because'): 'because' is anchored as an added item; F024 ('since' = because) is a label-right EQUIVALENT, E024/F022 are UNDECIDABLE per authors. E035 ('primeiro... depois' vs 'só depois de'): the 'only' flag is asserted as a difference though the order is the same (label EQUIVALENT is right).
F019 ('la que más vendió' vs 'nadie vendió más que'): the negative quantifier 'nadie' is read as a prohibition (DO vs DONT); label EQUIVALENT is right. Proven-EQUIVALENT recall 0/30: paraphrases of voice, comparison and role are not recognised (all INCONCLUSIVE), as expected for a rule comparator.
Family table: restrictive_relative_clause carries every false-EQUIVALENT; causal_vs_temporal carries 3 of 5 wrong NOT_EQUIVALENT. Limits: two model authors (fresh instances of Opus and Sonnet), 80 pairs, author labels; nothing in the code was changed during the run.
## AFTER the run (code changed; the evaluator now refuses to re-run) — development evidence only
Defects fixed with tests on OWN sentences (tests/test_semantic_r.py, 4 new tests, 10 cases): (1) a comma before who/which/que/quem/quien is meaning: it stays in the identity check (norm) and raises AMBIGUOUS_RELATIVE_COMMA, so restrictive vs non-restrictive is never proven EQUIVALENT (the identical-message shortcut had hidden it);
(2) 'because / porque' on one side only is never an added item (INCONCLUSIVE, causation vs sequence not modelled); (3) a negative subject at clause start (nadie / nobody / ninguém / no one) raises UNREPRESENTABLE_NEGATIVE_QUANTIFIER, never read as a prohibition ('send it to no one' stays an object);
(4) 'only after / só depois de' mid-clause raises UNREPRESENTABLE_ONLY_TIME (a clause-initial 'solo después' keeps its earlier proven-equivalence behaviour).
Post-hoc on the same 80 pairs (NOT a result: the set is spent and the fixes were written knowing the failures): false-EQUIVALENT 0/50 (was 4), NOT_EQUIVALENT precision 6/6 (was 6/11), proven-EQUIVALENT recall still 0/30, INCONCLUSIVE 74/80 (was 65): the fixes bought safety by giving up the 4 EQUIVALENT verdicts, all of them wrong.
Unchanged: blind19 0/48 and 14/17, blind20 0/49 and 12/15, SemAntoNeg 0 false-EQUIVALENT / 2970 NOT_EQUIVALENT / 8 wrong. Full suite 1576 passed. Fourth set in a row that failed a gate for different reasons: any new claim needs blind22 by authors who have seen none of this.
