"""AIXL 0.3 = compact SERIALIZATION of the semantic graph (ATOM:VALUE tokens). The graph stays the core.
ASSUMPTION: intents/goals/atoms keep the 0.2 vocabulary (validated in 0.2 experiments); 0.3 only adds encodings for
quantities (K:QTY=), modality (N:NO_x + K:FORBID_x, K:ALLOW_x), aggregates (D:TOTAL_x), visibility, before/after."""
from aixl.core.semantic_graph import SemanticGraph
from aixl.legacy02.core.encoder import encode as _encode
from aixl.legacy02.core.parser import parse as _parse, AixlError


def encode(graph: SemanticGraph) -> str:
    return _encode(graph.to_frame(), do_normalize=True)


def decode(aixl: str) -> SemanticGraph:
    """Raises AixlError (code INVALID_AIXL / VERSION_MISMATCH) on malformed input."""
    return SemanticGraph.from_frame(_parse(aixl))


__all__ = ["encode", "decode", "AixlError"]
