# Preregistration — USE_LIMIT_PLURAL (a structural signal for "who is the audience") on a NEW fresh set (2026-10-29), evaluated ONCE

Why: two closed-list approaches failed on fresh data (E-USE-LIMIT v5 and v8: events and occasions are as open as audiences). New signal: a strong audience verb whose complement has a PLURAL HEAD (English: last word of the
noun phrase; Spanish/Portuguese: first word after the determiner). Events and occasions are mostly singular (`the harvest festival`), audiences mostly plural (`investors`, `los pacientes de diálisis`). No event list, no group list.
Design and variant choice used ONLY the spent sets (v5, v8): plural head scored audiences 96 % / 84 % and decoys 2 % / 0 % there; that is exploration, NOT evidence. Code frozen by hash BEFORE the data exist (FREEZE.json).
Known weak spots, tested on purpose: SINGULAR group audiences (`the committee`, `la junta directiva`, `a equipe médica`) and PLURAL events/purposes (`the weekly meetings`, `las pruebas de carga`).
Authors: THREE models (Opus -> out_A, Sonnet -> out_B, Haiku -> out_C), NOT given the repository, the code or any previous data. Each writes 60 fresh records (es 18, en 18, pt 24), with `subkind`:
 * 30 `open_audience`: strong audience verb + a group of people / an organisation of the author's choice, from varied domains. 20 `plural_group` (investors, patients...), 10 `singular_group` (a collective noun: the committee, the crew, la junta, a equipe).
 * 30 `decoy`: same verbs, complement NOT an audience. 20 `other` (events, occasions, purposes starting with a verb, deadlines, technical targets, projects, phases, campaigns) and 10 `plural_event` (plural events, periods, tasks or targets:
   the weekly meetings, las pruebas de carga, os testes de regressão, the quarterly reviews, the nightly builds).
 Fields: `source`, `faithful_light`, `limit_drop` (the relay loses ONLY that complement), `complement`, `kind`, `subkind`.
The outputs are written before anyone (including the evaluator) reads them; only line counts are reported back.
Hypotheses (decided now; the family is judged on the WHOLE set, hard subkinds included, and the subkinds are reported):
 X1  `open_audience` limit_drop flagged by the plural family >= 75 %   (reported per subkind: plural_group expected high, singular_group expected LOW — a finding, not a failure of X1 unless the total drops below 75 %)
 X2  `decoy` drop flagged by USE_LIMIT_PLURAL <= 10 %   (plural_event decoys included: the known weak spot)
 X3  faithful_light flagged by USE_LIMIT_PLURAL alone <= 3 %
 X4  equivalent pairs of the older sets with a USE_LIMIT_PLURAL alarm: 0 of 1 280 (checked before the freeze: see FREEZE notes)
 X5  spent v3 set: recipient decoy flagged by USE_LIMIT_PLURAL <= 3 %
Baselines scored on the same data: the default families (closed list) and the open mode (strong verb + any group). Reported regardless: per language, author and subkind, every missed audience, every decoy false alarm.
A failing hypothesis is reported, not repaired; no tuning after reading.
