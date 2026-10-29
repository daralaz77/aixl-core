# Preregistration — USE_LIMIT v7 VALIDATION on a NEW fresh set (2026-10-29), evaluated ONCE

Why: v5 failed W2 (decoy alarms 43.3 %); v6/v7 were tuned post-hoc on that same data (RESULT_v7_posthoc: decoy 3.3 %, open audiences 96.7 %), so those numbers are NOT evidence. This round tests the CURRENT code (v7 + the `summer` / `destinado às`
fixes, commit c6c4dc3) on data nobody tuned on. The code is frozen BEFORE the data exist (FREEZE.json hashes it; the data hashes are added when the files are complete); nothing is changed after reading.
Authors: THREE models (Opus -> out_A, Sonnet -> out_B, Haiku -> out_C), NOT given the repository, the code, the lists or any previous data. Each writes 60 fresh records (es 18, en 18, pt 24):
 * 30 `open_audience`: a strong audience verb (written for / aimed at / addressed to / tailored for / dirigido a / escrito para / voltado a ...) + a group of PEOPLE or an organisation of the author's choice, from domains DIFFERENT from the usual
   office ones (health, agriculture, education, public sector, NGOs, retail, manufacturing, energy, sport, culture). Fields `source`, `faithful_light`, `limit_drop`.
 * 30 `decoy`: the same verbs with a complement that is NOT an audience, chosen widely: events and occasions (ceremony, festival, harvest, election, anniversary), compound noun phrases whose head comes last in English, purposes starting with a
   verb, quantities and deadlines, technical targets (cluster, pipeline, schema), projects, phases, campaigns. Fields `source`, `faithful_light`, `drop`.
Same hypotheses as v5, decided now (baseline = the v4 code, data/use_limits_v5/baseline_invariants_v4.py.txt, scored on the same data):
 W1  `open_audience` limit_drop flagged by the current `relay_check` >= 75 %
 W2  `decoy` drop flagged by USE_LIMIT <= 10 %
 W3  faithful_light (both kinds) flagged by USE_LIMIT alone <= 3 %
 W4  equivalent pairs of the older sets with a USE_LIMIT alarm: 0 of 1 280
 W5  regression on the spent v3 set: recipient decoy <= 3 % and faithful_light flagged by USE_LIMIT alone <= 3 %
Reported regardless: per language and author, every missed open_audience drop, every decoy false alarm with its complement, and the v5 frozen numbers for comparison. A failing hypothesis is reported, not repaired.
