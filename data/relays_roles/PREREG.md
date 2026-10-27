# Preregistration — roles on FRESH model-written relays (2026-10-26), evaluated ONCE

Why: the swapped-role improvement (DELEGATION, second-person addressee) was designed after reading the 8 missed cases of data/relays (a spent set), so its 2 -> 8 of 10 is not evidence.
Authors: two models (Opus -> out_A, Sonnet -> out_B), told to act as an intermediate agent, NOT given the repository, the code, the previous data or the families. Each writes
its OWN 45 fresh instructions (ES / EN / PT, about 15 each; half name people, half use only roles / teams / departments) and, per instruction:
`faithful_light` (near-verbatim), `faithful_heavy` (strongly reworded), `role_swap` (ONE realistic swap of who does what or to whom, in one of four styles:
actor_flip, addressee_to_you, delegation, two_roles_swap) and `control` (one non-role corruption: negation, number, date_time or condition).
The outputs are written before anyone (including the evaluator) reads them; only line counts are reported back.

Frozen code: FREEZE.json (sha256 of aixl/invariants.py, the translator, completeness, numberwords and service; RELAY_FAMILIES). Nothing is tuned after reading.
Hypotheses (decided now):
 R1  role_swap relays flagged by `relay_check` >= 50 %   (the number to beat: 2 of 10 before the change)
 R2  faithful_light relays flagged <= 10 %
 R3  control corruptions flagged >= 70 %   (sanity: the detector still works on the non-role kinds)
 R4  each of the four role-swap styles flagged >= 30 %   (reported per style; a style at 0 is a finding even if R1 is met)
Reported regardless: faithful_heavy flagged (expected high: not a gate), the missed role swaps, which families fired on faithful_light.
