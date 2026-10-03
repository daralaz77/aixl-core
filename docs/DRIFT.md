# Drift
`detect_drift_graphs(source, target)` (`aixl/core/drift.py`) is a thin layer over the comparator: level = worst severity among concrete differences; `critical=True` flags CRITICAL_DRIFT. Reports always include the concrete differences (removed negation, dropped constraint/condition, changed target, quantity or time change), never only a label.
Tested: negation loss, target substitution, constraint loss, condition loss, "outside the organization" scope loss (`tests/test_properties.py`). Directional: adding detail to a safe action stays at base severity; removing/changing escalates.
Not yet: a standalone `round_trip()` / fidelity metric (GAP-3).
