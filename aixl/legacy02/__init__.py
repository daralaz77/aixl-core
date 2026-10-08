"""STABLE FOUNDATION (historical name \"legacy02\" -- this is NOT dead code). The AIXL 0.2 base the whole product is built on:
the wire syntax (core.encoder / core.parser), SemanticFrame, the normalizer, intent/goal derivation (protocol.atoms) and the rule
tables + `analyze` (translators.natural_to_semantic) that the 0.3 translator extends. It is a leaf: it must import nothing from the rest of
`aixl` (enforced by tests/test_architecture.py, ADR-022). Renaming it was considered and deferred (ADR-022, option B)."""
