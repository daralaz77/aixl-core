# Arena (adversarial self-test loop)
`python -m lab.arena.arena run --rounds 30 --seed N` · `replay` · `selftest`
Attackers mutate seeds; oracles with ground truth by construction judge; failures are minimized (seed shrunk, mutant regenerated with the same operator+seed), deduped by signature, stored in `failures.jsonl`, and re-used as seeds; attacker weights rise only for NEW distinct defects (state.json).
Results 2026-10-10 (≈20 seeds-rounds ×60 attacks, own-author seeds): 1 uncontained defect found+fixed (runs of spaces dropped "esta semana" while the gate said AIXL), 1 contained (lowercase/ALL-CAPS names lost by translator, gate falls back NATURAL). 0 WIRE crashes/hangs. A clean arena is not proof of correctness.

## Scope: what each number is about  (`python -m lab.arena.arena scope`, fixed seed, writes nothing)
An earlier version of this file said "0 META-FALSE-EQUIVALENT". That was true **only for the experimental comparator** (`aixl.semantic`). Per layer, over 844 meaning-changing mutants:

| layer | result | how to read it |
|---|---|---|
| experimental comparator (`aixl.semantic`) | 0 EQUIVALENT | the layer the old README number referred to |
| integrity envelope (`envelope.verify`) | **0 MATCH** (205 MISMATCH, 639 UNVERIFIED) | shipped; abstains instead of guessing |
| token gate (`translate_gated`) | 8 AIXL / 836 NATURAL, **0 collapsed** | see the caveat below |
| core comparator (`aixl.compare`) | **24 EQUIVALENT** | KNOWN limit of the closed lexicons, not a defect; patterns in `LIMITATIONS.md` ("E-ARENA-SCOPE") |

**Caveat on the gate row.** Until 2026-10-10 *none of the 22 seeds ever took the AIXL path of the gate*, so the oracles `META-GATE-DROPPED-NUMBER/NEGATION/COLLAPSE` had never fired in a real run (0 AIXL out of 737 was vacuous). Four dedicated `GATE_SEEDS` now reach it, but only a handful of mutants (8 of 844, all `num_change`) do, so this is a thin check, not strong evidence. What shows the oracles *can* fire is `selftest`: it plants 5 bugs (comparator says EQUIVALENT, decoder drops a prohibition, gate drops a number, envelope MATCHes a meaning change, gate collapses two meanings into one AIXL) and requires all 5 to be flagged.
The envelope and gate oracles are in `judge_meta`, so `run` now attacks them too; `replay` reports `CONTAINED` (not `FIXED`) for a failure the translator still has but the gate contains.

## Paraphrase attack, blind judges (2026-10-10)
48 pairs (24 SAME / 24 DIFFERENT, written first) judged by two blind subagents (haiku, sonnet) under `rules_v1.txt`, ids shuffled.
2-of-2 accuracy 47/48; **false-same 0** (no single judge either); 1 false-different (compare vs contrast). Through `hybrid.decide`: DIFFERENT 24/24 correct, SAME 21/24 (2 REVIEW because rules saw a diff, 1 false-different).
Small n, own-author pairs: it shows no failure here, not that the arbiter is safe. Judges stored in data/arena/judges/.
