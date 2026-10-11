# Arena (adversarial self-test loop)
`python -m lab.arena.arena run --rounds 30 --seed N` · `replay` · `selftest`
Attackers mutate seeds; oracles with ground truth by construction judge; failures are minimized (seed shrunk, mutant regenerated with the same operator+seed), deduped by signature, stored in `failures.jsonl`, and re-used as seeds; attacker weights rise only for NEW distinct defects (state.json).
Results 2026-10-10 (≈20 seeds-rounds ×60 attacks, own-author seeds): 1 uncontained defect found+fixed (runs of spaces dropped "esta semana" while the gate said AIXL), 1 contained (lowercase/ALL-CAPS names lost by translator, gate falls back NATURAL). 0 META-FALSE-EQUIVALENT, 0 WIRE crashes/hangs. A clean arena is not proof of correctness.

## Paraphrase attack, blind judges (2026-10-10)
48 pairs (24 SAME / 24 DIFFERENT, written first) judged by two blind subagents (haiku, sonnet) under `rules_v1.txt`, ids shuffled.
2-of-2 accuracy 47/48; **false-same 0** (no single judge either); 1 false-different (compare vs contrast). Through `hybrid.decide`: DIFFERENT 24/24 correct, SAME 21/24 (2 REVIEW because rules saw a diff, 1 false-different).
Small n, own-author pairs: it shows no failure here, not that the arbiter is safe. Judges stored in data/arena/judges/.
