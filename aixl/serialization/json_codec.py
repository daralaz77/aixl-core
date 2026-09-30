"""JSON = debug/interchange representation of the SemanticGraph."""
import json
from aixl.core.semantic_graph import SemanticGraph


def dumps(graph: SemanticGraph, indent: int | None = 2) -> str:
    return json.dumps(graph.to_dict(), ensure_ascii=False, indent=indent)


def loads(s: str) -> SemanticGraph:
    return SemanticGraph.from_dict(json.loads(s))


def canonical_json(graph: SemanticGraph) -> str:
    """Stable canonical form (tuples -> lists) used by tests and by the drift/compare engine."""
    c = {k: (list(v) if isinstance(v, tuple) else v) for k, v in graph.canonical().items()}
    return json.dumps(c, ensure_ascii=False, sort_keys=True)
