# veto = "all" vs "definite" (2026-11-18; spent sets, evidence only)
Sets: blind33 (270 fresh pairs, `data/blind33/hybrid/`) and 360 adversarial pairs drawn from earlier audits (240 not-equivalent, 120 equivalent; `data/blind33/hybrid_adversarial/`). Judges: Sonnet + Haiku, blind, 2-of-2.

| | veto="all" (default) | veto="definite" |
|---|---|---|
| blind33: SAME on equivalents (of 135) | 117 | **129** |
| blind33: false SAME (of 135) | 0 | 0 |
| adversarial: SAME on equivalents (of 120) | 110 | **112** |
| adversarial: false SAME (of 240) | 3 | 3 |

The 3 false SAME of the adversarial set are the same under both settings ('No, fewer than five days' / 'No/ fewer ...', 'No, not yet' / 'No not yet'): pairs whose label is itself arguable (the kind of mark after an answer word is not meaning); no veto reason applied to them.
Judges alone: Haiku alone said SAME on 44 of 240 not-equivalent pairs (18 %), Sonnet alone on 4, both (2-of-2) on 3: the second judge is what makes SAME safe, not the comparator's veto. The veto caught 0 judge errors in 630 pairs and cost 22 equivalents (17 + 5) with veto="all".
Limits: 'definite' is opt-in because 630 pairs with no observed judge error are not proof the veto never helps (upper bound of the error rate on the hard set about 1.3 %); judges and authors are Claude models.
