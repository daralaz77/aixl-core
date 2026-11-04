# blind23 (80 pairs) — pre-registration, written 2026-11-04 BEFORE the pairs exist
Purpose: first fresh test of the rule comparator (`compare_texts`) after the closed list DEFINITE_PATHS (commit 8a4c680). blind19-22 are SPENT and the list was chosen looking at them (in-sample 34/37 = 91.9% NOT_EQUIVALENT precision), so nothing about it is proven yet.
Project goal (user decision 2026-11-04): NO SILENT FAILURE. G1 is therefore the gate that decides the claim; G2 and recall are reported, not claimed, unless they pass on their own.
Families are ALL NEW: none of the 10 below was used in blind19-22 or to tune any rule: ellipsis_gapping (Ana sent the file and Luis the report / ... and Luis too), relative_time_deixis (yesterday / last week / two days ago / next Monday / the day before),
possession_part_whole (X's Y / the Y of X / X has Y / Y belongs to X), optionality_requiredness (required / optional / if available / where applicable), mood_imperative_vs_statement (do X / X is done / X should be done / X will be done),
prerequisite_dependency (X requires Y / do Y before X / X only after Y / X depends on Y), range_boundaries (between 3 and 5 / from 3 to 5 / up to 5 / at most 5 / 3 through 5, inclusive or not),
definiteness_reference (the file / a file / any file / that file / the same file), collective_vs_distributive (together / each / separately / as a group / one by one), state_vs_change (is open / opens / was opened / stays open / remains).
Code frozen by hash in CODE_FREEZE.json at commit 8a4c680 (the file hashes include the closed list and `Verdict.suspected`). Authors: two fresh agents (Opus and Sonnet; if one fails, the replacement is recorded here before any pair exists), 40 pairs each, no tools, nothing about AIXL, its code or its results;
only the family list, the label definitions and the schema. 4 pairs per family per author, about 40 / 40 / 20 EQUIVALENT / NOT_EQUIVALENT / UNDECIDABLE, es / en / pt mixed.
Scope: the SEMANTIC comparator alone (rule-based, offline). No arbiter or hybrid claim. `Verdict.suspected` is reported (how many non-EQUIVALENT pairs carry a suspected difference) but is not a verdict.
Gates:
  G1 (decides the claim) false-EQUIVALENT <= 3% of the non-EQUIVALENT-labelled pairs (UNDECIDABLE included), every id listed. Reported next to it, always: INCONCLUSIVE rate, NOT_EQUIVALENT recall, proven-EQUIVALENT recall (a comparator that answers INCONCLUSIVE to everything also passes G1).
  G2 (reported; claimed only if it passes by itself) NOT_EQUIVALENT precision >= 90% of the pairs the semantic calls NOT_EQUIVALENT.
  G3 reported only: proven-EQUIVALENT recall, NOT_EQUIVALENT recall, INCONCLUSIVE rate.
  G4 per-family table of false-EQUIVALENT and wrong NOT_EQUIVALENT.
Claim policy: "the rule comparator does not fail silently on text by other authors (new families)" may be stated ONLY IF G1 passes, worded narrowly (80 pairs, author labels, two model families that also wrote earlier sets) and together with the INCONCLUSIVE rate and NOT_EQUIVALENT recall. "NOT_EQUIVALENT is reliable on other authors' text" needs G2 too.
Labels are the authors' and are NOT corrected after the run; disputed labels are listed with both readings, gates use the original labels. One run, on frozen code; the evaluator refuses a second run and refuses if code or pair files changed.
Do not write the result file by shell redirection before the evaluator has run (blind21 lesson: the guard reads its existence); capture stdout, then write the file with an editor tool.
Expectation written beforehand: G1 holds (0 false-EQUIVALENT in 5 earlier sets, and the closed list can only turn NOT_EQUIVALENT into INCONCLUSIVE, never into EQUIVALENT); INCONCLUSIVE stays about 80-90% and proven-EQUIVALENT recall near 0. G2 is the open question: expected 80-95%, with the 3 known wrong types (deontic, action) the likeliest to repeat.
If a gate fails the finding is "not yet reliable outside the tuned constructions", not an excuse to relabel.
Honest limits written beforehand: two model authors; labels come from models, not humans; 80 pairs give a wide interval; with most verdicts INCONCLUSIVE, G1 passing says little about meaning and a lot about fail-closed behaviour.

## RESULT (run once on the FROZEN code at 8a4c680, 2026-11-04; raw output RESULT_run1.txt) — set is now SPENT
Pairs: Opus I001-I040 + Sonnet J001-J040 = 80 (33 EQUIVALENT, 30 NOT_EQUIVALENT, 17 UNDECIDABLE). Verdicts: 68 INCONCLUSIVE, 7 NOT_EQUIVALENT, 5 EQUIVALENT.
| gate | result | verdict |
|---|---|---|
| G1 false-EQUIVALENT <= 3% (decides the claim) | **3/47 = 6.4%** (I030, I038, J029) | **FAIL** |
| G2 NOT_EQUIVALENT precision >= 90% | **4/7 = 57.1%** | **FAIL** |
| G3 (report only) | proven-EQUIVALENT recall 2/33 = 6.1%; NOT_EQUIVALENT recall 4/30 = 13.3%; INCONCLUSIVE 68/80 = 85.0% | — |
Claim policy outcome: "does not fail silently on new families" is NOT allowed. First false-EQUIVALENT since blind16 and the first on a set run AFTER the project goal became "no silent failure". My expectation written beforehand (G1 holds) was wrong.
The 3 silent failures are two real classes, labels not disputed: (1) definite vs indefinite article ignored: 'el archivo' / 'un archivo' (I030), 'the file' / 'a file' (J029): articles are treated as function words and dropped, so the pair looks identical; (2) tense/aspect ignored: 'The ticket was closed' / 'The ticket is closed' (I038): event in the past vs current state (the author's own what_differs says so; a reasonable reader may call it near-equivalent, but gates use the original label).
G2 wrong NOT_EQUIVALENT: I028 and J025 (range 'between 1 and 10' vs 'from 1 to 10, inclusive' / 'entre 3 y 5' vs 'de 3 a 5': UNDECIDABLE by the authors, inclusivity open: a range is compared as range vs two exact numbers), J030 (EQUIVALENT: 'cualquier' vs 'todo' in a universal-obligation context: quant any vs all asserted).
Family table: false-EQUIVALENT in definiteness_reference (2) and state_vs_change (1); wrong NOT_EQUIVALENT in range_boundaries (2) and definiteness_reference (1). 2 non-EQUIVALENT pairs are INCONCLUSIVE with a suspected difference (the closed list working as designed).
The closed list DEFINITE_PATHS did not cause any of the 3 silent failures (all three have an empty diff list: the comparator never saw the difference). It did what it was meant to (2 suspected differences kept) but did not touch G1, which was the goal.
Limits: two model authors, 80 pairs, author labels; nothing in the code was changed during the run.
