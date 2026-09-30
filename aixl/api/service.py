"""Public API (spec §28). Pure Python, no external service."""
from aixl.translators.natural_to_semantic import to_graph
from aixl.serialization import aixl_codec, json_codec
from aixl.core.semantic_graph import SemanticGraph
from aixl.core.comparator import compare_graphs, format_diff, ComparisonResult
from aixl.core.drift import detect_drift_graphs, DriftReport
from aixl.core.ambiguity import detect_ambiguity_graph, AmbiguityResult
from aixl.core.contradiction import detect_contradiction_graphs, ContradictionResult
from aixl.negotiation import negotiate as _negotiate, NegotiationOutcome


def to_semantic(text: str) -> SemanticGraph:
    return to_graph(text)


def to_aixl(text: str) -> str:
    return aixl_codec.encode(to_graph(text))


def from_aixl(aixl: str) -> SemanticGraph:
    return aixl_codec.decode(aixl)


def translate(text: str) -> dict:
    """Text -> {semantic (canonical form), graph (JSON), aixl, ambiguity, warnings}."""
    g = to_graph(text)
    c = {k: (list(v) if isinstance(v, tuple) else v) for k, v in g.canonical().items()}
    return {"input": text, "semantic": c, "graph": g.to_dict(), "aixl": aixl_codec.encode(g),
            "ambiguity": detect_ambiguity_graph(text, g).to_dict(), "warnings": g.meta.get("warnings", [])}


def compare(text_a: str, text_b: str, config: dict | None = None) -> ComparisonResult:
    return compare_graphs(to_graph(text_a), to_graph(text_b), config)


def compare_aixl(aixl_a: str, aixl_b: str, config: dict | None = None) -> ComparisonResult:
    return compare_graphs(aixl_codec.decode(aixl_a), aixl_codec.decode(aixl_b), config)


def semantic_diff(text_a: str, text_b: str) -> str:
    return format_diff(to_graph(text_a), to_graph(text_b))


def detect_drift(source: str, target: str, config: dict | None = None) -> DriftReport:
    return detect_drift_graphs(to_graph(source), to_graph(target), config)


def detect_ambiguity(text: str) -> AmbiguityResult:
    return detect_ambiguity_graph(text)


def detect_contradiction(text_a: str, text_b: str) -> ContradictionResult:
    return detect_contradiction_graphs(to_graph(text_a), to_graph(text_b))


def negotiate(text_sender: str, text_receiver: str, max_rounds: int = 3, config: dict | None = None,
              today=None) -> NegotiationOutcome:
    """E-NEGOTIATE (spec §NEGOTIATE, 2026-09-30): resolve a disagreement between two independently-encoded
    readings of two natural-language texts via the bounded clarification exchange (aixl/negotiation.py).
    `text_sender` is treated as authoritative (the party holding the original instruction); `text_receiver`
    is the other agent's own independent reading. See `negotiate_aixl` for two already-encoded AIXL lines,
    the more common real use case (E-INTEROP: two vendors' own encodings, not two raw texts)."""
    sender_g, receiver_g = to_graph(text_sender, today), to_graph(text_receiver, today)
    return _negotiate(sender_g.canonical(today=today), receiver_g.canonical(today=today), config, max_rounds)


def negotiate_aixl(aixl_sender: str, aixl_receiver: str, max_rounds: int = 3, config: dict | None = None,
                    today=None) -> NegotiationOutcome:
    """Same as `negotiate`, but from two AIXL lines already produced independently by two agents/vendors —
    decoded by the unmodified codec, exactly like `compare_aixl`."""
    sg, rg = aixl_codec.decode(aixl_sender), aixl_codec.decode(aixl_receiver)
    return _negotiate(sg.canonical(today=today), rg.canonical(today=today), config, max_rounds)


def explain(text: str) -> dict:
    """Semantic-firewall groundwork (spec §38): what does the agent want, on what object, under which constraints,
    is it forbidden/allowed? (No enforcement in 0.3.)"""
    g = to_graph(text)
    c = g.canonical()
    return {"wants": [a for a in c["actions"]], "objects": list(c["data"] + c["entities"] + c["references"]),
            "constraints": list(c["constraints"] + c["modifiers"] + c["quantities"]), "conditions": list(c["conditions"]),
            "modality": list(c["negation"]) or ["REQUEST"], "ambiguous": detect_ambiguity_graph(text, g).ambiguous}
