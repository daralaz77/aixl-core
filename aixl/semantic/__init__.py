"""EXPERIMENTAL -- not on the `import aixl` path. May import only `core` and the root API (tests/test_architecture.py, ADR-022). Reached by the
published hybrid MCP tool via aixl/hybrid_protocol.py and by aixl.atoms. Its \"safer than the arbiter\" claim was NOT established (blind rounds 17-18).

AIXL 0.3-R semantic track (parallel to aixl.core; does not change aixl.compare).
parse(text) -> SemanticObject (typed atoms, provenance, explicit ambiguity);  compare(a, b) -> Verdict (fail-closed, 3-state)."""
from aixl.semantic.compare import compare, compare_texts  # noqa: F401
from aixl.semantic.hybrid import HybridDecision  # noqa: F401
from aixl.semantic.hybrid import decide as hybrid_decide  # noqa: F401
from aixl.semantic.model import Atom, Diff, SemanticObject, Step, Verdict  # noqa: F401
from aixl.semantic.parser import parse  # noqa: F401
