"""AIXL 0.3 — experimental semantic core (representation, equivalence, diff, drift, ambiguity, contradiction)."""
from aixl.api.service import (translate, to_semantic, to_aixl, from_aixl, compare, compare_aixl, semantic_diff,  # noqa: F401
                              detect_drift, detect_ambiguity, detect_contradiction, explain, negotiate, negotiate_aixl,
                              semantic_fingerprint, semantic_fingerprint_aixl, validate, round_trip)

__version__ = "0.4.0"
