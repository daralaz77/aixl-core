# Preregistration — UNION of the closed audience list and the plural-head signal, on a NEW fresh set (2026-10-29), evaluated ONCE

Why: v9 showed the two signals are complementary (post-hoc): the closed list catches singular groups (collective nouns are a small closed class), the plural head catches plural groups; plural EVENTS remain a hole.
Design changes made BEFORE this data (informed by the v9 misses, which are SPENT): (1) English head rule: the noun phrase is cut at a post-modifier (`of ...`, a participle `visiting ...`) before taking its last word;
(2) more natural strong audience verbs (`directed at`, `designed for`, `conceived for`, `adapted for/to`; `adaptado a`, `concebido para`, `focado em`, `feito para`). On the spent sets the union scored 89 % of audiences, 5 % of ordinary decoys,
93 % of plural events (exploration, NOT evidence). Union = the default families (USE_LIMIT, closed list) OR USE_LIMIT_PLURAL (`RELAY_FAMILIES_PLURAL`). Code frozen by hash BEFORE the data exist (FREEZE.json).
Authors: THREE models (Opus -> out_A, Sonnet -> out_B, Haiku -> out_C), NOT given the repository, the code or any previous data. 60 records each (es 18, en 18, pt 24) with `subkind`:
 * 30 `open_audience`: 20 `plural_group` (in ENGLISH at least half with a post-modifier: `the tenants of the Maple Street building`, `school groups visiting the museum`, `volunteers who help at the shelter` is NOT allowed — only `of ...` and participles),
   10 `singular_group` (collective nouns: committee, crew, board, junta, equipe, comissão, conselho).
 * 30 `decoy`: 20 `other` (events, occasions, purposes starting with a verb, deadlines, technical targets, projects, phases, campaigns) and 10 `plural_event` (plural events, periods, tasks or targets).
 Fields: `source`, `faithful_light`, `limit_drop`, `complement`, `kind`, `subkind`. Outputs are written before anyone reads them; only line counts are reported back.
Hypotheses (decided now; the union is judged on the WHOLE audience set, hard subkinds included):
 Y1  `open_audience` limit_drop flagged by the union >= 75 %   (per subkind and language reported)
 Y2  ORDINARY decoys (`other`) flagged by the union <= 10 %
 Y3  English `open_audience` flagged by the union >= 60 %   (the target of design change 1; v9 plural family alone: 37 %)
 Y4  faithful_light flagged by the audience families alone <= 3 %
 Y5  equivalent pairs of the older sets with a USE_LIMIT or USE_LIMIT_PLURAL alarm: 0 of 1 280
 Y6  spent v3 set: recipient decoy flagged by the audience families <= 3 %
Reported regardless (no bar): `plural_event` decoys (the known hole, expected high), the overall decoy rate, `singular_group` and `plural_group` recall, every missed audience and every false alarm, and the default and open modes on the same data.
A failing hypothesis is reported, not repaired; no tuning after reading.
