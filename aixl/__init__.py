"""AIXL 0.3 — experimental semantic core (representation, equivalence, diff, drift, ambiguity, contradiction)."""
from aixl.api.service import (  # noqa: F401
                              compare,
                              compare_aixl,
                              detect_ambiguity,
                              detect_contradiction,
                              detect_drift,
                              explain,
                              from_aixl,
                              negotiate,
                              negotiate_aixl,
                              round_trip,
                              semantic_diff,
                              semantic_fingerprint,
                              semantic_fingerprint_aixl,
                              to_aixl,
                              to_semantic,
                              translate,
                              validate,
)

__version__ = "0.5.0"
