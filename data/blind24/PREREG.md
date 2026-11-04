# blind24 (80 pairs) — pre-registration, written 2026-11-04 BEFORE the pairs exist
Purpose: fresh test of the rule comparator (`compare_texts`) after the blind23 fixes (commit 4525428: indefinite article, past/future marker, range vs from-to, any vs all). blind19-23 are SPENT; each exposed constructions the parser drops or mis-models, and G1 failed on blind23 (3/47). The fixes were written knowing those failures, so none shows yet whether they generalise.
Project goal (user decision 2026-11-04): NO SILENT FAILURE. G1 decides the claim; G2 and recall are reported, not claimed, unless G2 passes by itself.
Families are ALL NEW: none of the 10 below was used in blind19-23 or to tune any rule: tense_bare_verb_forms (sent / sends / will send / has sent / envió / envía / enviará; the known remaining gap of the tense check), number_singular_plural (the file / the files / each file / all files),
percentage_vs_absolute (10% of / 10 units / one in ten / half of / a third), permission_scope_who (anyone / only admins / members / owners / everyone except), reversibility_finality (permanently delete / move to trash / archive / can be undone / irreversible),
hedging_certainty (will / might / probably / is expected to / is guaranteed / should be fine), information_source_evidence (confirmed / reportedly / allegedly / according to the log / as stated in), repetition_count (once / twice / again / every time / one more time),
time_of_day_timezone (9am / 9:00 UTC / noon / end of day / business hours / local time), domain_terms_near_synonyms (cancel / postpone / suspend, delete / archive, refund / credit, approve / acknowledge).
Code frozen by hash in CODE_FREEZE.json at commit 4525428. Authors: two fresh agents (Opus and Sonnet; if one fails, the replacement is recorded here before any pair exists), 40 pairs each, no tools, nothing about AIXL, its code or its results;
only the family list, the label definitions and the schema. 4 pairs per family per author, about 40 / 40 / 20 EQUIVALENT / NOT_EQUIVALENT / UNDECIDABLE, es / en / pt mixed.
Scope: the SEMANTIC comparator alone (rule-based, offline). No arbiter or hybrid claim. `Verdict.suspected` is reported but is not a verdict.
Gates (identical to blind23):
  G1 (decides the claim) false-EQUIVALENT <= 3% of the non-EQUIVALENT-labelled pairs (UNDECIDABLE included), every id listed. Reported next to it, always: INCONCLUSIVE rate, NOT_EQUIVALENT recall, proven-EQUIVALENT recall (a comparator answering INCONCLUSIVE to everything also passes G1).
  G2 (reported; claimed only if it passes by itself) NOT_EQUIVALENT precision >= 90% of the pairs the semantic calls NOT_EQUIVALENT.
  G3 reported only. G4 per-family table.
Claim policy: "the rule comparator does not fail silently on text by other authors (new families)" may be stated ONLY IF G1 passes, worded narrowly (80 pairs, author labels, two model families that also wrote earlier sets) and together with the INCONCLUSIVE rate and NOT_EQUIVALENT recall. "NOT_EQUIVALENT is reliable on other authors' text" needs G2 too.
Labels are the authors' and are NOT corrected after the run; disputed labels are listed with both readings, gates use the original labels. One run, on frozen code; the evaluator refuses a second run and refuses if code or pair files changed.
Do not write the result file by shell redirection before the evaluator has run; capture stdout, then write the file with an editor tool.
Expectation written beforehand (blind23 taught me not to promise G1): I expect AT LEAST ONE false-EQUIVALENT, most likely in tense_bare_verb_forms (the check only covers auxiliaries) and possibly in number_singular_plural, percentage_vs_absolute or repetition_count (numerals/plurals the parser may treat as filler). INCONCLUSIVE about 80-90%, proven-EQUIVALENT recall near 0-10%, G2 uncertain (fewer than 10 NOT_EQUIVALENT calls expected).
If a gate fails the finding is "not yet reliable outside the tuned constructions", not an excuse to relabel.
Honest limits written beforehand: two model authors; labels come from models, not humans; 80 pairs give a wide interval; with most verdicts INCONCLUSIVE, G1 passing says little about meaning and a lot about fail-closed behaviour.

## RESULT (run once on the FROZEN code at 4525428, 2026-11-04; raw output RESULT_run1.txt) — set is now SPENT
Pairs: Opus K001-K040 + Sonnet L001-L040 = 80 (27 EQUIVALENT, 37 NOT_EQUIVALENT, 16 UNDECIDABLE). Verdicts: 69 INCONCLUSIVE, 9 NOT_EQUIVALENT, 2 EQUIVALENT.
| gate | result | verdict |
|---|---|---|
| G1 false-EQUIVALENT <= 3% (decides the claim) | **2/53 = 3.8%** (K006, L007) | **FAIL** (one fewer error would have passed: 1/53 = 1.9%) |
| G2 NOT_EQUIVALENT precision >= 90% | **4/9 = 44.4%** | **FAIL** |
| G3 (report only) | proven-EQUIVALENT recall 0/27; NOT_EQUIVALENT recall 4/37 = 10.8%; INCONCLUSIVE 69/80 = 86.2% | — |
Claim policy outcome: "does not fail silently on new families" is NOT allowed. My written expectation ('at least one false-EQUIVALENT') was right, but about the wrong family: tense_bare_verb_forms had 0 false-EQUIVALENT (the blind23 tense fix held on these 8 pairs); the failures are in number_singular_plural.
Silent failures, one class, labels not disputed for K006 (singular vs plural, author NOT_EQUIVALENT), author UNDECIDABLE for L007 ('o relatório' / 'os relatórios'): the comparator ignores singular vs plural of the noun ('attachment' / 'attachments' is folded to the same lemma, and the article 'the' does not change).
G2 wrong NOT_EQUIVALENT: K005 (cada vs todos: each vs all, UNDECIDABLE: author itself says per-file vs set reading is open), K009 and L009 ('one in ten' vs '10%': EQUIVALENT: 'one' and 'ten' are read as two exact numbers, a fraction expressed in words as a quantity), K012 ('a third' vs '30%': UNDECIDABLE: a numeric fraction word dropped as a reference), L036 ('business hours' vs 'between 9am and 5pm': UNDECIDABLE: a named period vs explicit times).
Family table: false-EQUIVALENT in number_singular_plural (2); wrong NOT_EQUIVALENT in percentage_vs_absolute (3), number_singular_plural (1), time_of_day_timezone (1). 2 non-EQUIVALENT pairs are INCONCLUSIVE with a suspected difference.
Reading: G1 over three consecutive new-family sets (blind22 0/47, blind23 3/47, blind24 2/53) is 5/147 = 3.4% pooled, always in constructions the parser folds away (article, tense, number). The fixes are local, each blind set finds a new fold. Limits: two model authors, 80 pairs, author labels; nothing in the code was changed during the run.
