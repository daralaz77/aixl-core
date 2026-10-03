# Semantic model specification

## Layers (never mixed)
`text (ES/EN/PT)` → **translator** → `SemanticGraph` → **canonical()** → { AIXL line | JSON | comparator }. Language parsing, normalization,
encoding, transport and execution are separate modules (`aixl/translators`, `aixl/core`, `aixl/serialization`, `aixl/adapters`+`aixl/agents`).
Nothing executes. See [../ARCHITECTURE.md](../ARCHITECTURE.md) for the module table.

## Graph
`SemanticObject(id, type, value, attributes, confidence, source)` — types `ACTION, ENTITY, DATA, TIME, LOCATION, REFERENCE, CONSTRAINT,
CONDITION, QUANTITY, OUTPUT, MODIFIER, INTENT, RESIDUE`. `RESIDUE` (additive 2026-10-02) holds a literal clause no other node could represent. `confidence` is the **extraction** confidence, never part of the meaning.
`SemanticRelation(source, relation, target)` — `TARGET, TIME, LOCATION, REFERENCE, BEFORE, …`. An ACTION node carries
`modality ∈ {REQUEST, FORBID, ALLOW}` and `order`. Nothing is invented: absent time/location/format stay empty (`NOT_SPECIFIED`).

## Canonical form (what comparison, fingerprint and negotiation use)
`SemanticGraph.canonical(config=None, today=None)` returns 16 dimensions:
`intent, actions, entities, data, time, location, constraints, conditions, negation, references, quantities, goal, output, modifiers, bindings, residue` (`residue` = the order-free, light-stemmed content words of all `RESIDUE` nodes; empty for graphs without any).
Conservative normalization only — it must never turn a real difference into equivalence:
action synonym groups (`data/config.json: action_groups`), `EXCLUDE X` ≡ `FORBID INCLUDE X`, numbers (`.90`=`0.9`, `1.000`=`1000`),
duration units (1 year = 12 months), generic `DATA` dropped when a specific datum exists, relative time resolved against `today`
(default: system date), aggregates kept distinct (`TOTAL_SALES` ≠ `SALES`). Intent and goal are *derived*, scored but never
reported as an independent difference. Unordered dimensions are compared as sets; `actions` order is meaningful.

## Comparison
`compare()` returns `equivalent` (exact on the canonical form), a weighted `similarity` (configurable, **experimental**, not truth),
`verdict ∈ EQUIVALENT, NOT_EQUIVALENT, INCONCLUSIVE` (INCONCLUSIVE only when `config["inconclusive"]` is true: the canonical forms match but equality is not proven — see [COMPARATOR.md](COMPARATOR.md)), `drift_level ∈ NO_DRIFT, MINOR_, MODERATE_, MAJOR_, CRITICAL_DRIFT` (worst difference), typed `differences`
(`field, source, target, kind ∈ changed|added|removed|order, severity`), `critical_changes`, and `warnings` (transparency, never a verdict change).

Severity (`data/config.json`, configurable): negation, quantities → CRITICAL; time, constraints, conditions, references, actions, data, output → MAJOR;
entities, location → MODERATE; goal, intent → MINOR. Escalations: opposite/destructive action changes; critical constraint keys
(`VISIBILITY, BEFORE, AFTER, TIME_AT, RECIPIENT, SCOPE`); and — **context-sensitive and directional** — when a destructive/external action
(`DELETE, EXECUTE, SEND, DISABLE, UPDATE`) is involved, a *removed or changed* reference/object/condition/constraint is CRITICAL (target/scope
changed, safeguard dropped); `added` keeps its base severity. TIME = MAJOR is an **assumption** (the two source specs disagreed).

### Warnings (§66 — loss and uncertainty are reported, not hidden)
| `type` | Meaning |
|---|---|
| `UNRECOGNIZED_TERMS` (per side) | an object noun outside the closed lexicon was not represented; equivalence/partial verdicts may overstate agreement |
| `NO_ACTION_RECOGNIZED` (`BLOCKING`) | no action recognised in a text; an "equivalent" verdict proves nothing |
| `UNACCOUNTED_CONTENT` | (`inconclusive` on, rule-based graphs) canonical forms match but each text has content words no slot represents |
| `INCOMPLETE_ENCODING` | (`inconclusive` on, graphs annotated with `completeness`) a side drops content or an unreflected structural marker, or the markers differ; equality not proven |
| `OBFUSCATION:*` (in `graph.meta["warnings"]`) | invisible characters / compatibility forms / mixed-script homoglyphs were normalised |

## Mapping to the six statuses of §22 (derived, not a native field)
`EQUIVALENT` = `equivalent`; `PARTIALLY_EQUIVALENT` = not equivalent and **all** differences are the same kind (all `added` or all `removed`), none NEGATION
(a mix of removed+added is a replacement ⇒ `NOT_EQUIVALENT`); `CONTRADICTORY` = `detect_contradiction`; `AMBIGUOUS` = `detect_ambiguity`;
`INSUFFICIENT_CONTEXT` ≈ the `NO_ACTION_RECOGNIZED` warning. This mapping is exactly what `benchmarks/sil5x100_eval.py` implements.

## Detectors
* **Ambiguity** (heuristic): pronoun with no/multiple antecedents, vague time, missing year/target/scope/comparand, unresolved "the old ones",
  generic object under a destructive action. Blocking reasons set `ambiguous=True`; INFO notes (relative date needs an anchor, unrecognized terms) do not.
* **Contradiction**: explicit opposition on the *same object* — request vs forbid, allow vs forbid, ENABLE/DISABLE, INCLUDE/EXCLUDE, PUBLIC/PRIVATE, BEFORE/AFTER, reversed steps.
  Not implicit or intra-text contradictions.
* **Fingerprint**: `semantic_fingerprint()` = SHA-256 (first 16 hex) of the canonical form; same meaning ⇒ same hash across language, word order, punctuation, synonyms.

## Known limits of the model
**Measured on other authors' open-domain text (EVIDENCE.md):** the model is only as complete as its slots. Whatever has no slot is dropped without trace, so on blind10/blind11 the rule-based route judged 40–59 % of non-equivalent pairs "equivalent". `R:` residue + completeness make the loss visible but cannot prove two different wordings equal (best AIXL-side pipeline: 32 % of true paraphrases). Use the full-text arbiter for open text; use this model where the vocabulary is controlled.
Flat frame (actions are not paired with their own targets), closed vocabulary (25 actions, ~20 nouns), conditions mostly literal strings,
weeks unresolved. Full list with evidence: [../LIMITATIONS.md](../LIMITATIONS.md).
