# blind33 - pre-registration (written BEFORE the single run; authors never saw the comparator or any fix)

Set: 270 fresh pairs (135 EQUIVALENT / 135 NOT_EQUIVALENT; en 99, es 91, pt 80) from three authors (opus, sonnet, haiku) who were told only the construct families
(negation scope, excepted set, short answers, which time/day belongs to which action, which modal belongs to which action, bound + number, roles, conditions), never the code, the tests or any fix.
Authors' labels are the ground truth; no judges. Code is frozen by sha256 of every aixl/semantic/*.py before the run (CODE_FREEZE.json); the run refuses a second execution.

Three trees, same pairs: V071 = main 6db46d2 (published), P0005 = main + patch 0005 (negation scope / exception number / answer marks closed), NEW = P0005 + slot binding + relative-clause negation + closed-shape rewrites
('which/who'='that' before an auxiliary, 'have to'='must', '5 or more'='at least 5', 'a minimum of', ', but <clause>'='; <clause>').

A pair counts as FALSE ACCEPT if either direction returns EQUIVALENT on a NOT_EQUIVALENT-labelled pair; as PROVEN if BOTH directions return EQUIVALENT on an EQUIVALENT-labelled pair.

Rules (all must hold for the change to be called an improvement; otherwise it is reported as not demonstrated):
- R-safety: NEW adds 0 false accepts that P0005 and V071 did not already have (paired).
- R-binding: NEW false accepts <= P0005 false accepts.
- R-recall: NEW proven - P0005 proven >= +3 of the 135 EQUIVALENT-labelled pairs.
- R-loss: NEW loses <= 2 proofs that P0005 had.
Reported without a rule: per-language and per-family tables, V071 vs P0005 vs NEW, every false accept and every newly proven / lost pair.
Known limits: authors are Claude models (isolated by instruction, not technically); one construction, one run; the rewrite rules were chosen after reading the equivalents of an earlier audit (audit 5), so only blind33 is a test of them.
