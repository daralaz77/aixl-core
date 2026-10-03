# Architecture Decision Records (master prompt §82)
Format: Problem / Decision / Alternatives / Reasoning / Consequences / Compatibility. Each ADR records evidence where it exists; none claims more than was measured. Semantic changes and their migration are in [../SEMANTIC_CHANGELOG.md](../SEMANTIC_CHANGELOG.md).

| ADR | Decision |
|---|---|
| 001 | Graph is the core; AIXL is a serialization |
| 002 | Exact canonical equivalence; similarity only diagnostic |
| 003 | Closed lexicons, no fuzzy synonyms |
| 004 | LLMs propose, the Core validates |
| 005 | Confidence is metadata, not evidence |
| 006 | Relative time resolves at canonicalization with explicit date |
| 007 | Context-sensitive severity for destructive/external actions |
| 008 | Unknown words reported, never silent |
| 009 | "Most recent" is a constraint |
| 010 | Action–argument binding (K:BIND) |
| 011 | Provenance outside the canonical form |
| 012 | validate() / round_trip() pure and structured |
| 013 | Ambiguity with context never picks |
| 014 | No execution in the Core |
| 015 | Fingerprints: canonical, version-bound, conservative |
| 016 | Open role slots + explicit residue + INCONCLUSIVE verdict (AIXL 0.5, DESIGN ONLY) |
| 018 | AIXL 0.5 scope: exact engine (controlled vocabulary) + loss detector + interchange/audit layer around a full-text arbiter (ACCEPTED 2026-10-03) |
| 017 | Residue canonicalizer (independent per-side keys) + per-side completeness check (DESIGN) |

ADRs 001–008, 014 and 015 record decisions made earlier in the project, written down on 2026-10-02 from the code, tests and the benchmark notes; the evidence they cite is in BENCHMARK.md and LIMITATIONS.md. ADRs 009–013 were decided and measured on the same day.
