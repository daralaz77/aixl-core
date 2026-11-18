# blind33 end-to-end hybrid (2026-11-18, spent set, evidence only: judges are fresh, labels are the authors', not pre-registered)
Two independent judges (Sonnet, Haiku; blind, shuffled ids, `rules.txt` = arbiter rules v1, id 9e63b85575c5caf5) on the 270 blind33 pairs; `aixl.semantic.hybrid.decide` combines them with the rule-based comparator of each tree.

| 135 equivalent pairs | judges 2-of-2 alone | hybrid, comparator 0.7.1 | hybrid, + patch 0005 | hybrid, + binding / shapes (this change) |
|---|---|---|---|---|
| SAME | 134 | 115 | 115 | **117** |
| REVIEW (a person decides) | 0 | 19 | 19 | 17 |

| 135 non-equivalent pairs | judges alone | hybrid (all three comparators) |
|---|---|---|
| false SAME | 0 | 0 (DIFFERENT 135) |

Reading: on these pairs the judges alone made no mistake, so the comparator's veto added no measured safety here and cost 17 of 135 equivalents (they go to REVIEW: 9 suspected differences, 8 ambiguity flags). Its measured value is elsewhere (earlier evidence: hybrid false-SAME 2.9 % vs 54 % for the rule-based comparator alone, docs/EVIDENCE.md). The judges are Claude models and so are the authors: shared blind spots are not measured by this table.
