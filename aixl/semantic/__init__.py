"""AIXL 0.3-R semantic track (parallel to aixl.core; does not change aixl.compare).
parse(text) -> SemanticObject (typed atoms, provenance, explicit ambiguity);  compare(a, b) -> Verdict (fail-closed, 3-state)."""
from aixl.semantic.model import Atom, Step, SemanticObject, Verdict, Diff      # noqa: F401
from aixl.semantic.parser import parse                                         # noqa: F401
from aixl.semantic.compare import compare, compare_texts                       # noqa: F401
from aixl.semantic.hybrid import decide as hybrid_decide, HybridDecision      # noqa: F401
