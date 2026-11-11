# Semantic changelog (master prompt §83)
Format per change: VERSION · CHANGE · BACKWARD COMPATIBILITY · MIGRATION · TEST IMPACT. Package version is `aixl.__version__`; the wire token stays `V:AIXL-0.3`.

## 0.4.0 — 2026-10-02
Canonical form gains a dimension, so by VERSIONING_POLICY.md this is a loud MINOR while MAJOR is 0.

| Change | Backward compatibility | Migration | Test impact |
|---|---|---|---|
| `ORDER=MOST_RECENT`/`OLDEST` constraint (ADR-009) | Texts with "más reciente/latest/mais recente/último <noun>" now differ from the same text without it; old AIXL lines unchanged | Re-fingerprint stored texts containing those phrases | `test_composition.py` |
| `bindings` canonical dimension, `K:BIND=ACTION>ARG` (ADR-010) | Old AIXL decodes with empty bindings (unknown, not different). Lines with BIND are readable by 0.3 parsers as ordinary K constraints | Re-fingerprint multi-action texts; LLM encoders keep working without BIND | `test_bindings.py`; 0 verdict changes on 1400 labelled pairs |
| Node `provenance` (ADR-011) | JSON without it loads as EXPLICIT; canonical/fingerprint unaffected | none | `test_validate_roundtrip_provenance.py` |
| `validate()`, `round_trip()` (ADR-012) | New functions | none | same file |
| `detect_ambiguity(text, context=None)` (ADR-013) | Optional parameter; findings gain optional keys only with a context | none | `test_ambiguity_context.py` |
| Graph per-action TARGET/DEPENDS_ON/OBJECT edges, `meta.composition` | Edge relations already existed; JSON gains edges | none | `test_composition.py` |
| `aixl/resources/config.json`: `bindings` weight 3.0, severity MAJOR | Keys added | custom configs without them fall back to severity MAJOR and weight 3.0 (tested) | covered by `test_bindings.py` |

Regression tests added for property/invariant behaviour (`test_properties.py`, `test_golden.py`). Total at release: 435 passed.

## 0.7.1 — 2026-11-11 — universal quantifier on the subject; wire token stays `V:AIXL-0.3`
| Change | Backward compatibility | Migration | Test impact |
|---|---|---|---|
| 'each / every / cada / todo' and 'all / todos' on the subject are proven equal when nothing is counted, summed, excepted or ordered; exactly one plural carried by the quantified subject is not a difference | Some pairs that were INCONCLUSIVE now come out EQUIVALENT; strict mode unchanged; the mutation test records one case in `KNOWN_OPEN` as a deliberate policy change | none | `test_semantic_blind30.py`, `test_mutation_properties.py` |

## 0.7.0 — 2026-11-11 — strict hybrid and three comparator changes; wire token stays `V:AIXL-0.3`
| Change | Backward compatibility | Migration | Test impact |
|---|---|---|---|
| `hybrid_decide(..., require_semantic_equivalent=True)`, `hybrid_protocol.decide(..., strict=True)`, MCP `aixl_hybrid_decide(..., strict=True)`: a unanimous judge SAME is accepted only if `compare_texts` also proves EQUIVALENT, otherwise REVIEW | New optional parameter; default behaviour unchanged | none | `test_hybrid_protocol.py`, `test_mcp_integration.py` |
| Fixed deadline phrasings are proven equal ('no later than X' = 'by X', 'by X at the latest' = 'by X', 'no máximo até' = 'até', 'no después del' = 'hasta el'); a bare 'at the latest' stays content. Applied after the strict-mode token identity | Some pairs that were INCONCLUSIVE (or wrongly NOT_EQUIVALENT) now come out EQUIVALENT; strict mode unchanged | none | `test_semantic_recall_2026_11_11.py` |
| A fronted time or frequency adjunct ('After C, do A', 'Mañana, X', 'Cada semana, X', 'Every Monday, X') is moved to the end before parsing; before/after stay distinct | Same as above | none | same file |
| `never / nunca / jamás` and `qualquer / cualquier` on one side only enter the dropped-feature ledger | Some pairs that came out EQUIVALENT now come out INCONCLUSIVE (never the reverse) | none | same file |

Measured on 120 fresh pairs (`data/blind29`, old and new comparator on the same pairs): false accepts 2 to 1 of 60 with none new; proven equivalents 29 to 31 of 60 (3 gained, 1 lost; the pre-registered rule of +5 does NOT hold). Strict hybrid there: 1 of 60 false accepts and 31 of 60 equivalents, against 7 of 60 and 60 of 60 for the two judges alone. Evidence sets `data/blind26` to `data/blind29`; limits in `docs/HYBRID_MCP.md`. Total at release: 1,943 passed in the sandbox; the 20 local-server tests and one benchmark-import test need local ports or the network (they pass in CI).

## 0.6.0 — 2026-11-06 — the comparator asserts less and says "equal" less often; wire token stays `V:AIXL-0.3`
| Change | Backward compatibility | Migration | Test impact |
|---|---|---|---|
| `compare_texts(a, b, strict=False)`; `strict=True`: EQUIVALENT only for the same token sequence. MCP tool `aixl_compare_semantic`, CLI `semantic [--strict]` | New parameter, tool and command; default behaviour of `compare_texts` is the only thing below | none | `test_semantic_r.py` (strict), `test_mcp_integration.py`, CLI test |
| Closed list `DEFINITE_PATHS`: only reliable difference types (obligation, quantity, time, action, `only`, reference, recipient, quantifier, antonym, `without`, sequence, steps, condition polarity) may produce NOT_EQUIVALENT; others become INCONCLUSIVE and are kept in `Verdict.suspected` | `Verdict.to_dict()` gains a `suspected` key; pairs that were NOT_EQUIVALENT because of loose items / conditions / exceptions are now INCONCLUSIVE | callers that treat INCONCLUSIVE as "not proven equal" need no change | `test_semantic_r.py` (`FLAGGED`) |
| Dropped-feature ledger (indefinite article, past/future marker, plural, version-like numerals) blocks EQUIVALENT when it differs; `AMBIGUOUS_NOT_PROHIBITED` flag; each/all and any/all differences are suspected, not asserted | Some pairs that came out EQUIVALENT now come out INCONCLUSIVE (never the reverse) | none | blind19-25 post-hoc: 0 false-EQUIVALENT, same proven-EQUIVALENT except 2 pairs in blind19 |
| Regular expressions that were cubic or quadratic on digit runs fixed; numerals longer than 40 characters are treated as words | `to_semantic` on 2,000 digits: 19 s to under 0.1 s; no `ValueError` | none | `test_redos_budget.py` |

Total at release: 1,921 passed. Details of the evidence: `data/blind23` to `data/blind25` PREREG files.

## 0.5.0 — 2026-10-03 (ADR-016, ADR-017, ADR-018) — all opt-in or additive; wire token stays `V:AIXL-0.3`
| Change | Backward compatibility | Migration | Test impact |
|---|---|---|---|
| `ComparisonResult.verdict` (EQUIVALENT / NOT_EQUIVALENT / INCONCLUSIVE) | New field; `equivalent` unchanged unless `config["inconclusive"]` is true (default false) | none; with the flag on, callers that treated `equivalent=False` as "different" now also receive "not proven" | `test_inconclusive.py` |
| Atom `R:` / node `RESIDUE` / canonical dimension `residue` | Lines without `R` unchanged; a pre-`R` reader rejects a line containing it | none for old data; re-fingerprint only graphs that carry residue | `test_residue.py`; 453 → 462 tests, 0 regressions |
| `aixl.core.completeness` (per-side completeness, structural markers) used by `compare_graphs` when graphs are annotated and the flag is on | Not used otherwise | none | `test_completeness.py` |
| `residue_key` keeps 1–2 character content tokens; `ontology.DIMENSIONS` gains `residue` | residue dimension empty for old graphs ⇒ no verdict change | none | covered by the same tests |
| `aixl.arbiter` (rules id, 2-of-2 consensus, judge-output validation, `DecisionMemo`, `decide`) + `data/arbiter/rules_v1.txt` | New module; imports no provider and never calls a model | none | `test_arbiter.py` (16) |
| `canonical()` omits an EMPTY `residue` | Graphs without residue keep their exact 0.4.0 canonical form and fingerprint (golden pin `4d601cd77a368a82`) | none | `test_fingerprint.py` |
These changes make loss visible and refuse to say "equal" without proof; they do **not** make the comparator prove paraphrase equivalence ([EVIDENCE.md](EVIDENCE.md)).


## Unreleased — AIXL 0.4 atom layer (2026-10-04)
Added `aixl/atoms/` (registry 0.3.0, schema/canonical fingerprint, wire format, firewall/profile/alignment/diff, fidelity, controlled-domain fail-closed extractor), `cli.py atoms-*`, annotation guide v0.2→v0.4, gold + three blind sets, `benchmarks/atoms_report.py`, ADR-019, 29 tests (suite 610). `aixl.compare` and the 0.3-R track are unchanged. Honest status in docs/ATOMS.md.
