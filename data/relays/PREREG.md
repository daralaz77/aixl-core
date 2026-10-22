# Preregistration — relays written by real models (2026-10-22), evaluated ONCE

Sources: 120 instructions (data/arena/other_author_seeds.jsonl, seeded shuffle 2026, two halves of 60). Two model authors (Opus -> out_A, Sonnet -> out_B), told to
act as an intermediate agent and NOT given the repository: per source a `faithful_light` relay (near-verbatim), a `faithful_heavy` relay (strong rewording,
same meaning) and a `corrupted` relay with ONE subtle meaning change, 5 of each of 12 corruption types (negation, number, date_time, modality, condition,
conjunction, scope, entity, omission, antonym_verb, role_swap, pronoun_reference). Outputs were written BEFORE the code in this commit was frozen and were NOT read
by the evaluator before the freeze (only their line counts were reported).

Frozen code: see FREEZE.json (sha256 of aixl/invariants.py, the translator, modifiers and completeness; RELAY_FAMILIES). No threshold or family is tuned after reading.
Hypotheses (decided now):
 H1  corrupted relays flagged by `relay_check` >= 70 %
 H2  faithful_light flagged <= 5 %
 H3  faithful_heavy flagged <= 25 %   (heavy rewording legitimately moves slots; `relay_check` is not claimed for this regime)
 H4  the three former blind spots (antonym_verb, role_swap, pronoun_reference) each >= 50 % detected
Reported regardless of outcome: per-type detection, which families fired on faithful relays, and the corrupted relays that were missed.
