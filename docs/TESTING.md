# Testing
Run: `cd ~/.claude/skills/aixl-core && .venv/bin/python -m pytest tests -q` (system python has no pytest). 2026-10-03: 462 passed, 0 xfailed.
- Unit/integration: `test_equivalence, test_drift, test_ambiguity, test_contradiction, test_fingerprint, test_normalizer, test_objects, test_codec, test_demos, test_translator, test_mcp_*, test_a2a_*, test_negotiation`.
- Regression: `test_regression.py` (every bug, BUG-NNN). Security: `test_sil_security.py` (adversarial tier). Benchmarks: `test_sil5x100.py`, `benchmarks/`.
- Properties/invariants (new): `test_properties.py` — determinism, canonical stable under AIXL and JSON round-trip, fingerprint stability, self-equivalence, and invariants: negation must not disappear, target must not change silently, constraint/condition loss is drift, no invented time/target, cross-lingual convergence.
- Golden (new): `test_golden.py` pins critical canonical fields and ES/EN/PT convergence; changing it is a semantic change.
- Composition (new): `test_composition.py` (GAP-1/2 fixed). `test_known_gaps.py` was removed once all its gaps were closed; add strict-xfail tests there for new gaps. When a gap is fixed the test XPASSes and fails the suite until the file and LIMITATIONS are updated.
Honest scope: the prompt's 450-test target and per-category counts (§48) are not met as separate suites; the data sets (dev200, blind1-9, sil5x100, sil_security) cover most categories.

- `test_validate_roundtrip_provenance.py` (new): validate() structured issues and statuses, round_trip() fidelity incl. codec failure, provenance values and JSON survival.
- `test_ambiguity_context.py` (new): two-Juan demo in ES/EN/PT, surname/alias resolution, unknown vs ambiguous.
- `test_bindings.py` (new): swap detection (ES/EN/PT), AIXL round-trip of BIND, unknown-vs-difference, subset compatibility, unreliable clauses, synonym stability.

- `test_inconclusive.py`, `test_residue.py`, `test_completeness.py` (new 2026-10-02/03): the opt-in INCONCLUSIVE verdict (default behaviour unchanged), the `R:` atom (codec round-trip, one-sided residue is a difference, order-free), and per-side completeness/structural markers (short values like `sala B` ≠ `sala C`, before/after opposed, unreflected markers).
- Experiment harnesses (not unit tests; they read frozen outputs under `data/blind10/` so every published table recomputes without new model calls): `benchmarks/blind10_eval.py`, `blind10_llm_eval.py`, `completeness_eval.py`, `typed_keys_eval.py`, `residue_canon_eval.py`, `arbiter_eval.py`, `adversarial_eval.py`, `repeatability_eval.py`, `blind11_eval.py`, `funnel_eval.py`. Sets are verified with `shasum -a 256 -c data/blind10/blind1{1,2}.sha256`.
