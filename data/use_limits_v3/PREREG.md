# Preregistration — USE_LIMIT v3 (extended lexicon) on a NEW, LARGER fresh set (2026-10-29), evaluated ONCE

Why: the v1 set (data/use_limits) is SPENT: its 14 misses were read after the freeze and the lexicon was then extended (audience constructions with a verb — `written for`, `addressed to`,
`dirigido a`, `voltado aos`, `direcionado à` —, Portuguese legal/status phrasings, hyphenated forms, more group nouns). That extension is NOT evidence. This set tests it.
Authors: THREE models (Opus -> out_A, Sonnet -> out_B, Haiku -> out_C), told to act as an intermediate agent, NOT given the repository, the code, the previous data or the lexicon. Each writes 50 fresh
records (es 15, en 15, pt 20; Portuguese is over-weighted on purpose: it was the weakest) with, per record: `source` (one use-limit marker of the given style), `faithful_light`, `faithful_heavy`,
`limit_drop` (relay that loses ONLY the marker), `control` (one non-marker corruption) and a RECIPIENT DECOY: `recipient_source` (an instruction that names a group as a plain RECIPIENT — send / deliver /
forward / post it to the board, the finance team, the auditors... — and contains NO use-limit marker) and `recipient_relay` (a faithful relay that rewords the recipient phrasing: other preposition or a synonym of the
group). Styles balanced (confidentiality, legal_status, audience, doc_status), audience written with the full range of constructions authors find natural (verbs, nouns, labels).
The outputs are written before anyone (including the evaluator) reads them; only line counts are reported back.

Frozen code: FREEZE.json (sha256 of aixl/invariants.py and its dependencies; RELAY_FAMILIES). Nothing is tuned after reading; a failing hypothesis is reported, not repaired.
Hypotheses (decided now):
 V1  limit_drop flagged by the new `relay_check` >= 80 % overall; every style >= 70 % (audience included); Portuguese >= 75 %
 V2  faithful_light flagged <= 10 %; flagged by USE_LIMIT alone <= 3 %
 V3  faithful_heavy flagged by USE_LIMIT alone <= 10 %
 V4  recipient_relay flagged by USE_LIMIT <= 3 %   (the decoy: a normal recipient must not read as a use-limit change)
 V5  control corruptions flagged >= 70 %
 V6  equivalent pairs of the older sets with a USE_LIMIT alarm stay at 0 of 1 280 (checked before the freeze: 0)
Reported regardless: per style and per language, per author, the missed limit_drops, the faithful_heavy USE_LIMIT alarms (which words), and the v1 frozen numbers for comparison.
