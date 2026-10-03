# Drift
`detect_drift_graphs(source, target)` (`aixl/core/drift.py`) is a thin layer over the comparator: level = worst severity among concrete differences; `critical=True` flags CRITICAL_DRIFT. Reports always include the concrete differences (removed negation, dropped constraint/condition, changed target, quantity or time change), never only a label.
Tested: negation loss, target substitution, constraint loss, condition loss, "outside the organization" scope loss (`tests/test_properties.py`). Directional: adding detail to a safe action stays at base severity; removing/changing escalates.
Not yet: a standalone `round_trip()` / fidelity metric (GAP-3).

**Evidence (2026-10-03):** drift levels are only as good as the extraction. On other authors' open text the comparator saw `NO_DRIFT` between pairs that differ in a recipient role, frequency or quantity phrasing, because those details never reached the graph; use `inconclusive` / the arbiter before trusting `NO_DRIFT` ([EVIDENCE.md](EVIDENCE.md)).
