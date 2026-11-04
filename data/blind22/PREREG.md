# blind22 (80 pairs) — pre-registration, written 2026-11-04 BEFORE the pairs exist
Purpose: a fresh test of the rule comparator (`compare_texts`) after the fixes that followed blind21 (commit 1ae0e5c). blind19, blind20 and blind21 are SPENT; each failed G2 and two failed G1, always on different constructions. Their fixes were written knowing their failures, so none of them can show whether the fixes generalise.
Families are ALL NEW: none of the 10 below was used in blind19-21 or to tune any rule: reported_speech_attribution (said that / according to / claims), counterfactual_hypothetical (if X had ..., would ... / if X, will ...), purpose_vs_result (in order to / so that / with the result that),
location_prepositions (in / on / under / inside / outside / next to), pronoun_reference_scope (his / her / their / it / the former / the latter), duration_vs_deadline (for 2 hours / within 2 hours / by Friday / until Friday), request_vs_command_register (please / could you / must / you may / feel free to),
modifier_attachment (old files and folders / red or blue cars / the first two tasks), cleft_and_contrastive_focus (it is X that ... / not Y but X / X rather than Y), aspect_completed_vs_ongoing (has finished / is finishing / started / will have finished).
Code frozen by hash in CODE_FREEZE.json at commit 1ae0e5c. Authors: two fresh agents (Opus and Sonnet; if one fails, the replacement is recorded here before any pair exists), 40 pairs each, no tools, nothing about AIXL, its code or its results;
only the family list, the label definitions and the schema. 4 pairs per family per author, about 40 / 40 / 20 EQUIVALENT / NOT_EQUIVALENT / UNDECIDABLE, es / en / pt mixed.
Scope: the SEMANTIC comparator alone (rule-based, offline). No arbiter or hybrid claim.
Gates, unchanged from blind19-21 so the four sets are comparable:
  G1 false-EQUIVALENT <= 3% of the non-EQUIVALENT-labelled pairs (UNDECIDABLE included), every id listed.
  G2 NOT_EQUIVALENT precision >= 90% of the pairs the semantic calls NOT_EQUIVALENT.
  G3 reported only: proven-EQUIVALENT recall, NOT_EQUIVALENT recall, INCONCLUSIVE rate.
  G4 per-family table of false-EQUIVALENT and wrong NOT_EQUIVALENT.
Claim policy: "the rule comparator generalises to text by other authors" may be stated ONLY IF G1 and G2 both pass, worded narrowly (new instances, 80 pairs, author labels, two model families that also wrote earlier sets).
Labels are the authors' and are NOT corrected after the run; disputed labels are listed with both readings, gates use the original labels. One run, on frozen code; the evaluator refuses a second run and refuses if code or pair files changed.
Do not write the result file by shell redirection before the evaluator has run (blind21 lesson: the guard reads its existence); capture stdout, then write the file.
Expectation written beforehand: the three recent fixes added many fail-closed flags, so G1 should hold more often than before and recall of proven EQUIVALENT will stay near zero; G2 depends on whether the few remaining definite diffs hit untuned constructions (pronoun scope, location, deadline vs duration are the likeliest).
If a gate fails the finding is "not yet reliable outside the tuned constructions", not an excuse to relabel.
Honest limits written beforehand: two model authors; labels come from models, not humans; 80 pairs give a wide interval; with most verdicts INCONCLUSIVE the precision rests on very few NOT_EQUIVALENT calls, so G2 can pass on a handful of pairs and say little.

## RESULT (run once on the FROZEN code at 1ae0e5c, 2026-11-04; raw output RESULT_run1.txt) — set is now SPENT
Pairs: Opus G001-G040 + Sonnet H001-H040 = 80 (33 EQUIVALENT, 30 NOT_EQUIVALENT, 17 UNDECIDABLE). Verdicts: 68 INCONCLUSIVE, 12 NOT_EQUIVALENT, 0 EQUIVALENT.
| gate | result | verdict |
|---|---|---|
| G1 false-EQUIVALENT <= 3% | **0/47 = 0.0%** | PASS |
| G2 NOT_EQUIVALENT precision >= 90% | **7/12 = 58.3%** | **FAIL** |
| G3 (report only) | proven-EQUIVALENT recall 0/33; NOT_EQUIVALENT recall 7/30 = 23.3%; INCONCLUSIVE 68/80 = 85.0% | — |
Claim policy outcome: "the rule comparator generalises to text by other authors" is NOT allowed (G1 holds, G2 fails). What the data support: no silent equivalence on 47 non-equivalent pairs from new families; the comparator still over-asserts definite differences. The comparator proved EQUIVALENT nothing at all (85% INCONCLUSIVE), so G1 passing is partly the price of that.
Reading of the 5 wrong NOT_EQUIVALENT (labels NOT corrected). Disputed labels: G008 ('if' vs 'only if', necessary vs sufficient: same dispute as B024 and C035; the author took the pragmatic reading), H040 (author UNDECIDABLE; 'started at noon' vs 'has started': an extra time item is anchored as a difference although the pair differs only by an added detail).
Comparator defects (labels right): H005 (English inverted conditional 'Had we shipped' vs 'If we had shipped': the inversion is not recognised, the condition is lost and a time is invented), H014 ('en la carpeta' vs 'dentro de la carpeta': a locative preposition 'dentro de' is anchored as an item), H021 ('en menos de dos horas' vs 'dentro de las próximas dos horas': less_than vs within are different slots for the same deadline).
Family table: no false-EQUIVALENT in any family; wrong NOT_EQUIVALENT in counterfactual_hypothetical (2), aspect (1), duration_vs_deadline (1), location_prepositions (1). Limits: two model authors (fresh Opus and Sonnet instances), 80 pairs, author labels; precision rests on only 12 NOT_EQUIVALENT calls; nothing in the code was changed during the run.
## AFTER the run (code changed; the evaluator now refuses to re-run) — development evidence only
Defects fixed with tests on OWN sentences (tests/test_semantic_r.py, 3 new tests): (1) an inverted conditional at clause start ('Had they paid', 'Were we', 'de haber') raises UNREPRESENTABLE_INVERTED_CONDITIONAL, never a lost condition plus an invented time;
(2) 'inside / dentro de' + a place (no number or time unit within 4 tokens) raises UNREPRESENTABLE_LOCATIVE; 'dentro de dos horas' stays a time slot and still compares; (3) 'in less than N units' and 'within the next N units' with the same N and unit are one deadline written two ways (INCONCLUSIVE, not a difference); different N stays NOT_EQUIVALENT.
Post-hoc on the same 80 pairs (NOT a result: the set is spent and the fixes were written knowing the failures): false-EQUIVALENT 0/47, NOT_EQUIVALENT precision 7/9 (was 7/12); the 2 wrong are exactly the disputed G008 and H040. Proven-EQUIVALENT recall still 0/33, INCONCLUSIVE 71/80.
Unchanged: blind19 0/48 and 14/17, blind20 0/49 and 12/15, blind21 0/50 and 6/6, SemAntoNeg 0 false-EQUIVALENT / 2970 NOT_EQUIVALENT / 8 wrong. Full suite 1580 passed. Five sets, each failing G2 on different constructions: patching by set does not converge on a generalisation claim; any new claim needs blind23 with families and authors never seen.
