"""AIXL 0.3 = compact SERIALIZATION of the semantic graph (ATOM:VALUE tokens). The graph stays the core.
ASSUMPTION: intents/goals/atoms keep the 0.2 vocabulary (validated in 0.2 experiments); 0.3 only adds encodings for
quantities (K:QTY=), modality (N:NO_x + K:FORBID_x, K:ALLOW_x), aggregates (D:TOTAL_x), visibility, before/after."""
from aixl.core.semantic_graph import SemanticGraph
from aixl.legacy02.core.encoder import encode as _encode
from aixl.legacy02.core.parser import AixlError
from aixl.legacy02.core.parser import parse as _parse
from aixl.legacy02.protocol.atoms import ACTIONS, INTENTS


def encode(graph: SemanticGraph) -> str:
    return _encode(graph.to_frame(), do_normalize=True)


def _check(frame, strict: bool) -> None:
    """Evolution Engine §7: a symbol the graph cannot carry must raise, never be silently dropped.
    The graph keeps a prohibition only through its action node, so an N:NO_x / K:FORBID_x without A:x would vanish.
    Unknown VALUES are tolerated by default (bug032: compared as not-equivalent, never crash); strict=True rejects them."""
    if strict:
        if frame.intent not in INTENTS and frame.intent != "UNKNOWN":
            raise AixlError("UNKNOWN_ATOM_VALUE", f"I:{frame.intent}")
        bad = [a for a in frame.actions if a not in ACTIONS]
        if bad:
            raise AixlError("UNKNOWN_ATOM_VALUE", "A:" + ",".join(bad))
    acts = set(frame.actions)
    for tok in list(frame.negations) + list(frame.constraints):
        for pre in ("NO_", "FORBID_", "ALLOW_"):
            if tok.startswith(pre) and tok[len(pre):] not in acts:
                raise AixlError("ORPHAN_NEGATION", f"{tok} has no matching A:{tok[len(pre):]}")


def decode(aixl: str, strict: bool = False) -> SemanticGraph:
    """Raises AixlError (INVALID_AIXL / VERSION_MISMATCH / UNKNOWN_ATOM_VALUE / ORPHAN_NEGATION) on input it cannot carry.
    Orphan prohibitions always raise; unknown atom values raise only with strict=True."""
    frame = _parse(aixl)
    _check(frame, strict)
    return SemanticGraph.from_frame(frame)


__all__ = ["encode", "decode", "AixlError"]
