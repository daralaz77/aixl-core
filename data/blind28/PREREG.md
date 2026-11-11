# blind28 (about 120 pairs) — pre-registration, written 2026-11-11 BEFORE the pairs exist
This is a REDO. A first attempt on 2026-11-06 was lost before any judge answer was read or evaluated (its working folder was in /tmp and was wiped between sessions); no result from it was ever seen. This time everything lives in a persistent folder and is copied into the aixl-core repository at the end.
Purpose: two things the earlier sets could not show. (1) blind26 and blind27 were vacuous for the strict rule because the comparator accepted none of the 180 pairs; here the pairs are written INSIDE the constructs the comparator handles (bounds, exceptions, exclusivity, negation forms, number forms, deadline direction, verb synonyms, word order, quantifiers), so it can accept, and "comparator AND judges" can be measured for real. (2) a judge that is NOT a Claude model: Qwen2.5-7B-Instruct (Q4_K_M, Apache-2.0, local, offline, run through a local llama-server; downloaded with the user's authorisation), to test whether another model family breaks the Claude judges' correlated errors.
Honest framing: these constructs are the ones the comparator was tuned on (blind19-25). The sentences are new and by new authors, so this is a test on UNSEEN SENTENCES OF TUNED CONSTRUCTS (in-distribution), not on new constructs. It cannot support a generalisation claim.
Code frozen at the working tree of aixl-core equal to git commit 933fb76 (main, clean, CI green); SHA-256 of the semantic files, hybrid_protocol.py, arbiter.py, arbiter_rules_v1.txt go into CODE_FREEZE.json before any judge runs. The Qwen model files' SHA-256 are recorded too.

Constructs (10), 4 pairs each per author:
 1 bounds_at_least_at_most (at least / no fewer than / minimum; at most / up to / no more than / maximum)
 2 exception_except_unless (except / unless / apart from / all but / if not)
 3 only_exclusivity (only / just / solely / nobody but)
 4 negation_forms (don't / do not / never / no / not any)
 5 conditional_order_if_unless (if A then B vs B if A; unless vs if not)
 6 number_forms (twenty / 20, 1,000 / 1.000, room 4B / 4-B, units spelled or abbreviated)
 7 deadline_direction (before / after / by / until / no later than / at the latest)
 8 verb_synonyms (send / mail / forward, delete / remove, create / generate, install / deploy, restart / reboot)
 9 word_order_voice (active / passive, fronted adverb or clause, topicalisation)
10 quantifier_all_each_any (all / every / each, some / any, none / not any)
Authors: three fresh agents, no tools except Write to one path each: Opus (O001-O040), Sonnet (S001-S040), Haiku (H001-H040). They get nothing about AIXL or any result; only the construct list, label definitions, schema, and short realistic sentences about office, IT and data operations. About 20 EQUIVALENT (swap one standard construct for its standard equivalent), 14 NOT_EQUIVALENT (one subtle detail changed, same construct), 6 UNDECIDABLE per author; es / en / pt mixed. Expected total 120 (60 / 42 / 18); G1 allows at most 1 false accept of the 60 non-EQUIVALENT pairs.

Judges (pairs anonymised, shuffled, no labels or construct, one pass, prompt = arbiter_rules_v1.txt verbatim, not changed after seeing results): Opus and Sonnet (fresh agents, as before) and Qwen2.5-7B-Instruct Q4_K_M answering each pair through a local llama-server (127.0.0.1), ChatML template, temperature 0, seed 28, the output constrained by a grammar to `Qnnn<TAB>SAME|DIFFERENT|UNSURE<TAB>reason`. An answer that does not parse counts as UNSURE.

Systems measured (fixed now):
 R0 comparator alone (default verdict EQUIVALENT = accept)
 R1 (PRIMARY) comparator EQUIVALENT AND Opus SAME AND Sonnet SAME
 R3 comparator EQUIVALENT AND all three judges SAME
 J2 Opus and Sonnet both SAME; J3 all three SAME; Qwen alone; Opus alone; Sonnet alone; default hybrid (the two Claude judges plus semantic veto) and strict hybrid.
Gates:
  G1 (decides): R1 false accepts <= 3% of the NOT_EQUIVALENT-labelled pairs (UNDECIDABLE included), every id listed. VACUITY RULE: if R1 proves fewer than 10 EQUIVALENT-labelled pairs, G1 is reported VACUOUS.
  G1b (reported, independent of the comparator): J3 (all three judges) false accepts <= 3%.
  Reported always: every rule's false accepts and proven-EQUIVALENT recall; the error overlap (a) between Opus and Sonnet, (b) between Qwen and the two Claude judges, (c) between the comparator and the judges; per-construct table; pairwise agreement of the judges.
Claim policy: no generalisation claim in any outcome (in-distribution constructs, model authors, small sample). If G1 passes non-vacuously, the narrow sentence is allowed: "on N new sentences of the comparator's constructs, comparator AND two judges accepted k of M non-equivalent pairs, and proved p of E equivalent ones", with the rule-of-three note. A third judge from another family may be described as useful only if it measurably reduces false SAME or the error overlap on this set.
Labels are the authors' and are not corrected; disputed labels are listed with both readings. One run on the frozen code; the evaluator refuses a second run; the result file is written with an editor tool.
Expectations written beforehand: the comparator proves 10-25 of the ~60 equivalents (non-vacuous); R0 false accepts 0-3 (the comparator alone is NOT expected to pass G1 cleanly: every earlier set found a new hole in a tuned construct); the two Claude judges 3-8% false SAME on the subtle pairs; Qwen alone 10-25% false SAME and lower recall than Claude; adding Qwen to the unanimity (J3) lowers false SAME by about a third and lowers the equivalent recall; the Qwen-versus-Claude error overlap is lower than the Opus-versus-Sonnet overlap but still above chance. If R1 is again vacuous the finding is that the comparator's recall, not the judges, blocks the strict rule even inside its own constructs.
Honest limits: tuned constructs; authors are Claude models; Qwen 7B is a small model run at Q4; one run; about 120 pairs; the Qwen answer is grammar-constrained and its reason is not informative.
