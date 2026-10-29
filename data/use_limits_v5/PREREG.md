# Preregistration — USE_LIMIT v5: a STRONG audience verb is the marker by itself (2026-10-29), evaluated ONCE on a NEW set

Why: v3 left audience at 83-86 % because the audience noun list is closed and any group can be an audience (`aimed at investors`, `dirigido a los inversionistas`, `pensado para os professores`).
Candidate v5: after a STRONG audience verb (written for / prepared for / aimed at / addressed to / dirigido a / escrito para / voltado a / redigido para / ...) ANY group counts as the audience, EXCEPT when the
complement is an event, a deadline, a number, a gerund/infinitive or a technical target (`prepared for the meeting`, `written for tomorrow`, `meant for testing`, `escrito para revisar`, `targeting the main branch`).
The exclusion lists and the verb list were written BEFORE this set and from general knowledge; the technical-target list came from ONE false alarm on an old, independent set (blind11), not from this data.
Authors: THREE models (Opus -> out_A, Sonnet -> out_B, Haiku -> out_C), NOT given the repository, the code or any previous data. Each writes 60 fresh records (es 18, en 18, pt 24):
 * 30 `open_audience`: an instruction containing a strong audience verb whose complement is a group of PEOPLE or an organisation of the author's own choosing (NOT the usual management/board/finance/auditors; e.g. investors,
   interns, patients, parents, tenants, volunteers, shareholders, freelancers, residents...). Fields `source`, `faithful_light`, `limit_drop` (the relay loses ONLY the `written for X` complement).
 * 30 `decoy`: an instruction with the SAME kind of strong verb whose complement is NOT an audience: an event, a deadline, a purpose, a quantity, a technical target, an occasion (`prepared for the meeting`, `written for tomorrow`,
   `aimed at reducing churn`, `geared to the Q4 close`, `dirigido a la rama principal`, `reservado para la reunión`, `voltado ao lançamento`...). Fields `source`, `faithful_light`, `drop` (the relay loses that complement).
The outputs are written before anyone (including the evaluator) reads them; only line counts are reported back.
Frozen code: FREEZE.json (sha256 of aixl/invariants.py and its dependencies). Baseline = the v4 code (saved before the v5 change) scored on the SAME data. Nothing is tuned after reading; a failing hypothesis is reported.
Hypotheses (decided now):
 W1  `open_audience` limit_drop flagged by the v5 `relay_check` >= 75 %   (v4 baseline reported)
 W2  `decoy` drop flagged by USE_LIMIT <= 10 %   (the risk: `prepared for the meeting` read as an audience marker)
 W3  faithful_light (both kinds) flagged by USE_LIMIT alone <= 3 %
 W4  equivalent pairs of the older sets with a USE_LIMIT alarm: 0 of 1 280 (checked before the freeze: 0)
 W5  regression on the spent v3 set: recipient decoy <= 3 % and faithful_light flagged by USE_LIMIT alone <= 3 %
Reported regardless: per language and author, every missed open_audience drop, every decoy false alarm with its complement, and the v4 numbers.
