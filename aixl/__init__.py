"""AIXL 0.3 — experimental semantic core (representation, equivalence, diff, drift, ambiguity, contradiction).

SAFE USE: `compare(...).equivalent` is reliable only inside the controlled vocabulary; on open text prefer `compare_verified(...)`, which never
answers EQUIVALENT without proof (see README §2 and LIMITATIONS.md, E-ARENA-SCOPE)."""
from aixl.invariants import relay_check  # noqa: F401, E402,I001
from aixl.api.service import (  # noqa: F401
                              compare,
                              compare_aixl,
                              compare_verified,
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
