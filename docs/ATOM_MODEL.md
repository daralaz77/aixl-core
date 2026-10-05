# AIXL 0.4 Atom Model v0.1 — annotation guide

Goal: turn one instruction (ES/EN/PT) into an **AtomGraph**: *atoms* (units of meaning) + *relations* (typed triples). Registry: `aixl/atoms/registry.py` (concept ids, atom types, relations).
Wire format is JSON. Ids (`a1`, `a2`…) are arbitrary; only the meaning counts.

## Atom
`{"id","type","concept","value","modality","polarity","scope","status"}` — omit what does not apply.
* `type`: ACTION, ENTITY, PROPERTY, QUANTITY, QUANTIFIER, TIME, LOCATION, FORMAT, CONDITION, REFERENCE, NAME.
* `concept`: a registry id (`ACT.SUMMARIZE`, `ENT.REPORT`, `PRP.EMPTY`, `FMT.PDF`). If the registry has no concept for a word, use an **extension** `x:<english lemma>` (e.g. `x:invoice_line`). Never use a "close" registry concept for a different thing (NO GUESS). Use `x:` for ACTION/ENTITY/PROPERTY/LOCATION only.
* ACTION `modality`: `DO` (default; imperative), `DONT` (prohibition/negation of the action), `MAY` (permission), `ADVISE` (should), `DISCOURAGE` (avoid), `NOT_REQUIRED` (no need to). One atom per action; never a separate NEGATION atom.
* QUANTITY: `value={"mode","n","unit"}`; mode ∈ exact|at_least|at_most|approx|more_than|less_than. A bare number with a unit and no qualifier is `exact`. Units: word, character, page, day, hour, minute, week, month, item, line, sentence, paragraph, mb, or `x:<lemma>` string in unit.
* QUANTIFIER: `value` ∈ all|some|each|any|none, attached to the entity it quantifies.
* TIME: `value={"rel","ref"}`; rel ∈ before (strictly earlier), until (inclusive limit: "hasta", "by", "no later than"), at, after, since, within, every. `ref`: weekday `mon..sun`, `today|tomorrow|yesterday`, ISO date `2026-10-05`, or `<n><unit>` like `24h`, `3day`. If the text is genuinely ambiguous between two rels (e.g. Spanish "antes del viernes" could include Friday), put the likelier in `value`, `status:"ambiguous"` and the other reading in `candidates:["until"]`.
* CONDITION: container; `value` = `if` (the body suffices) or `only_if` (necessary). Atoms that are the body of the condition carry `scope=<condition id>`. "unless X" = `if` with the body's polarity flipped on the negated part (`polarity:"-"` on the PROPERTY/ENTITY that is negated).
* REFERENCE: `value` = `prev` (it/them/lo/la/o/a referring back) or `other` (another/otro/outro).
* NAME: proper name, `value` = the name.
* `polarity:"-"`: negation of a PROPERTY/ENTITY inside a condition body ("if the file is **not** empty").

## Relations (triples `[src, REL, dst]`)
TARGETS (action→thing it applies to), RECIPIENT, AGENT (only if stated), SOURCE, HAS_PROPERTY (entity→property), QUANTIFIED_BY (entity→quantifier), CONSTRAINED_BY (action or entity→QUANTITY), OUTPUT_AS (action→FORMAT), OCCURS_AT (action→TIME), LOCATED_AT, CONDITIONED_BY (action→CONDITION), EXCLUDES (entity→the excluded subset-entity), RESTRICTS_TO (entity→the only allowed subset-entity), PRECEDES (action→action when order is stated or clearly sequential), REFERS_TO (REFERENCE→its antecedent).
**Exceptions/restrictions**: "all documents except the confidential ones" = ENTITY `ENT.DOCUMENT` (QUANTIFIED_BY all) + a second ENTITY `ENT.DOCUMENT` with HAS_PROPERTY `PRP.CONFIDENTIAL`, and `[doc1, EXCLUDES, doc2]`.
**Inside conditions**: the body's atoms (entity, property) are normal atoms with `scope=<cond id>`; the condition's own relations: `[action, CONDITIONED_BY, cond]`. Body entities are separate nodes from main-clause entities even if they denote the same noun.
**Multiple actions**: one ACTION atom each; each gets its own TARGETS etc.; add PRECEDES only for explicit order words (then, before, after, first, luego, depois, antes de) or "and then".

## Rules
* Represent only what the text says. Do not add atoms for what is implied (default modality DO is expressed by the field, not by inference).
* Do not transcribe words that carry no meaning (articles, "please").
* Quantity limits on the output ("in at most 150 words", "en máximo 150 palabras") = QUANTITY + `[action, CONSTRAINED_BY, qty]`.
* Counting quantity over an entity ("at least 3 files") = QUANTITY + `[entity, CONSTRAINED_BY, qty]`, unit `item`.

## Worked examples
1. "Resume el informe en máximo 150 palabras."
```json
{"atoms":[{"id":"a1","type":"ACTION","concept":"ACT.SUMMARIZE","modality":"DO"},{"id":"a2","type":"ENTITY","concept":"ENT.REPORT"},{"id":"a3","type":"QUANTITY","value":{"mode":"at_most","n":150,"unit":"word"}}],
 "relations":[["a1","TARGETS","a2"],["a1","CONSTRAINED_BY","a3"]]}
```
2. "If the file is not empty, send it to Ana before Friday."
```json
{"atoms":[{"id":"a1","type":"ACTION","concept":"ACT.SEND","modality":"DO"},{"id":"a2","type":"REFERENCE","value":"prev"},{"id":"a3","type":"ENTITY","concept":"ENT.FILE","scope":"c1"},{"id":"a4","type":"PROPERTY","concept":"PRP.EMPTY","polarity":"-","scope":"c1"},{"id":"c1","type":"CONDITION","value":"if"},{"id":"a5","type":"NAME","value":"Ana"},{"id":"a6","type":"TIME","value":{"rel":"before","ref":"fri"}}],
 "relations":[["a1","TARGETS","a2"],["a2","REFERS_TO","a3"],["a3","HAS_PROPERTY","a4"],["a1","CONDITIONED_BY","c1"],["a1","RECIPIENT","a5"],["a1","OCCURS_AT","a6"]]}
```
(In example 2 the property polarity is `-` on the PROPERTY atom.)

## Guide v0.2 — conventions fixed by adjudication of the first gold (3 annotators, 148 cases; disagreements resolved by majority or by these rules)
1. **Pronouns point at the ENTITY**, not at the action's product: "translate the text and send it" → REFERS_TO the text entity. An object that is simply absent ("depois assine", "envie ao cliente") is NOT represented (no implied atoms).
2. **"and" between actions** gets PRECEDES ONLY with an explicit order word (then, first, before, after, luego, depois, primero…). "Translate X and send it" has none (the gold had 2 inconsistent cases; corrected 2026-10-04 after audit).
3. **Negative quantifiers are canonical as negation**: `none of X` / `nada` / `nadie` / `to no one` = ACTION `DONT` + QUANTIFIER `any`. QUANTIFIER `none` is not used. "Copy none of the files" = `DONT` copy + `any`.
4. **every/todos/all → `all`; each/cada → `each`.**
5. **Time-unit limits are TIME `within`** (not QUANTITY): "within 24 hours", "in at most 2 hours", "en menos de 2 horas" → `{"rel":"within","ref":"24h"}`. Ref units: `h` hour, `min`, `d` day, `w` week, `mo` month. Output-size limits (words, characters, sentences, lines, pages, items, paragraphs) stay QUANTITY.
6. **Person objects**: call → TARGETS; notify, refund, pay, send-to → RECIPIENT.
7. **"check whether X is P"** is an embedded question, not a statement: ACTION `VERIFY` TARGETS a CONDITION container with `value:"whether"`; its body (scope=container) holds the entity (or a REFERENCE `prev` if the subject is elided) and the PROPERTY, linked by HAS_PROPERTY. It must differ from "if X is P, do Y".
8. `revis-` = ACT.REVIEW (read critically); `verific-/comprueb-/confirm-/valid-` = ACT.VERIFY. Accounting "cuenta/account" is `x:account`, not ENT.USER.
9. **Spanish/Portuguese "antes del/antes de"** → rel `before`, `status:"ambiguous"`, `candidates:["until"]`; English "before" is strict `before`; "by/hasta/until/até" → `until`.
10. **Bare today/tomorrow** → rel `at`.
11. **Double negation** ("no dejes de X") = plain DO. "Never"/"prohibido" = DONT (no stronger level in v0.1).
12. A body "it" in a condition ("delete the file only if it is empty") is a separate body ENTITY node with scope.

## Guide v0.3 — closes the gaps found when 3 models annotated 150 natural instructions (blind1, 2026-10-04). Registry 0.2.0. Supersedes anything above that conflicts.
Measured motivation: Sonnet-vs-Opus exact-graph agreement on natural text was 32.7 % (F1 81 %), versus 92.6 % on the author's own dev set. The disagreements were systematic: entity-to-entity links, compound nouns, TIME ref formats, first person, relative clauses.

**A. New relations** (registry 0.2.0): `OF` (ENTITY→ENTITY|NAME|REFERENCE: complement, possession, apposition, purpose: "contract of the lease", "Marta's quote", "customer Rodrigues", "order 4471" = ORDER OF NAME "4471", "bio for Dr. Okafor"), `RESULTS_IN` (ACTION→PROPERTY|ENTITY|NAME|LOCATION: "into French", "as reconciled", "in red", "into one spreadsheet"), `USING` (ACTION→ENTITY|PROPERTY: "tag with the event date", "pay with the corporate card").
Never use HAS_PROPERTY or SOURCE between two entities: it is `OF`. HAS_PROPERTY is only ENTITY→PROPERTY.

**B. Compound nouns**: a lexicalized noun-noun compound is ONE entity with an underscore concept (`x:shipping_label`, `x:press_release`, `x:api_key`, `x:brand_manual`, `x:subject_line`). A registry noun modified by a plain noun ("dentist appointment") = the registry entity plus the modifier as ENTITY linked by `OF`. Adjectives are PROPERTY. `x:` lemmas: English, lowercase, singular, base form, underscores.

**C. TIME ref grammar** (closed): weekday `mon..sun`; `today|tomorrow|yesterday|now`; ISO `YYYY-MM-DD`, `YYYY-MM`, `YYYY`; duration `<n>h|min|d|w|mo`; clock `HH:MM` (24 h); day of month `d1..d31`; month `jan..dec`; `(this|next|last)_(week|month|quarter|year|weekend)`; `month_start`, `month_end`; `event:<lemma>` for an event reference ("after the meeting" = `{after, event:meeting}`). rel adds `during`. A time that modifies a noun ("tickets closed since last quarter", "contracts of this quarter") attaches with `OCCURS_AT` from the ENTITY.

**D. First person**: me/my/mi/nosotros/-me clitics → ENTITY `ENT.SPEAKER`; "send me" = RECIPIENT speaker; "my appointment" = appointment OF speaker. An unspecified person/people = `ENT.PERSON`.

**E. Requirements without a verb** ("the report must have at most 5 pages", "no puede pasar de 60 caracteres"): ACTION `ACT.ENSURE` (modality DO for must/can't exceed, ADVISE for should), TARGETS the entity, CONSTRAINED_BY the QUANTITY.

**F. Actions inside a condition body** ("if the auditor asks for data"): ACTION atom with `scope=<condition id>`, AGENT / TARGETS relations as usual. Entity+property bodies stay as before. `whether` bodies follow the same rule.

**G. Negative adjectives** ("unsigned", "sin firmar"): PROPERTY with `polarity:"-"` anywhere (not only inside conditions).

**H. Explicit loss instead of forcing a bad model** — graph-level `"unrepresented": ["<source fragment>", ...]`. Use it (and do not model the fragment) ONLY for: restrictive relative clauses with a verb ("suppliers that ship to Chile"), distributive "per X"/"por X", exclusivity ("only admins can…": model the action with modality MAY and AGENT admin, and list `only admins`), comparatives without a number ("fewer colors"), evaluative remarks that are not instructions. Anything the guide does express MUST be modelled, not parked here.

**I. Ambiguity of words that match two registry concepts** (NO GUESS): use the registry concept only when the sentence's meaning is the registry definition. `devolver`/"give back" = `x:return`; "copy X on" (cc) = `x:cc`; "confirm the order" (accept) = `x:confirm`; `copia` of a document = `x:copy`.

**J. Possessive/ellipsis exceptions** ("except Maria's"): second ENTITY (same concept as the quantified one) `OF` NAME; `[first, EXCLUDES, second]`.

## Guide v0.4 — closes gaps found on blind2 (150 fresh texts, 2026-10-04). Registry 0.3.0. Wins over earlier sections.
Measured motivation: on unseen text Sonnet-vs-Opus exact-graph agreement was 35.3 % (F1 82.7 %); the remaining disagreement concentrated in actions that take actions, direction, dates, offsets and "without".
1. **Action as content of another action**: `CONTENT` (ACTION→ACTION): "remind me to pay" = remind CONTENT pay (+ RECIPIENT speaker); "ask Rafael to review X" = ask RECIPIENT Rafael, ask CONTENT review; "help me plan" = help CONTENT plan. `PURPOSE` for "so that / para que / in order to": do PURPOSE other. "because / porque" stays `unrepresented`.
2. **Direction**: `SOURCE` (ACTION|ENTITY → ENTITY|NAME|LOCATION|FORMAT) = "from X"; `DESTINATION` (ACTION|ENTITY → ENTITY|NAME|LOCATION|FORMAT) = "to X / into X as a place" ("shipment from Medellín to Cartagena", "convert from Excel to JSON"). `RESULTS_IN` can also take FORMAT/QUANTITY ("set to 18 degrees"). OF is still never directional.
3. **Dates**: month+day without year = `MM-DD` ("Oct 17" → `10-17`); parts of day `morning|afternoon|evening|night|dawn|noon|midnight`. Offsets: TIME value may carry `offset` (`<n>h|min|d|w|mo`): "1 month before expiration" = `{rel:before, ref:event:expiration, offset:1mo}`; "24 h before the appointment" = `{before, event:appointment, offset:24h}`. Ranges: two TIME atoms `since` + `until`.
4. **Subjects inside condition bodies and non-agents**: the subject of ANY verb is `AGENT` (even "the payment does not arrive", "the build fails"). The verb is an ACTION with `scope`.
5. **"without X" / "sin X" outside conditions**: an ENTITY with `polarity:"-"` linked by `OF` to what it lacks ("anything over $50 without a receipt" = anything OF receipt(polarity -)); inside a condition, same.
6. **Counts of an action** ("twice", "three times in a row"): QUANTITY `{exact,n,unit:"time"}` CONSTRAINED_BY the action. Manner ("remotely", "in writing"): PROPERTY via `RESULTS_IN`.
7. **Elided subsets** ("los críticos" of the open tickets): a second ENTITY of the same concept with the PROPERTY; no relation unless it is an exception (EXCLUDES) or "only" (RESTRICTS_TO).
8. **"I need X" / "necesito X"**: ACTION `x:need` with AGENT `ENT.SPEAKER` and TARGETS the needed thing (a deadline such as "before closing" is a TIME on `x:need`). If unsure, put the clause in `unrepresented`.
9. Anything still not covered: `unrepresented`, never forced.
