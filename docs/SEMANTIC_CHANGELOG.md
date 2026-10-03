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
| `data/config.json`: `bindings` weight 3.0, severity MAJOR | Keys added | custom configs without them fall back to severity MAJOR and weight 3.0 (tested) | covered by `test_bindings.py` |

Regression tests added for property/invariant behaviour (`test_properties.py`, `test_golden.py`). Total at release: 435 passed.
