"""Public API (spec §28). Pure Python, no external service required by default (AIXL_TRANSLATOR_MODE,
see aixl/translators/auto.py, is 'rule_based' unless explicitly changed — this module behaves exactly
as it did before the LLM-translator route existed, for every caller that doesn't opt in)."""
from typing import TYPE_CHECKING

from aixl.core.ambiguity import AmbiguityResult, detect_ambiguity_graph
from aixl.core.comparator import ComparisonResult, compare_graphs, format_diff
from aixl.core.contradiction import ContradictionResult, detect_contradiction_graphs
from aixl.core.drift import DriftReport, detect_drift_graphs
from aixl.core.semantic_graph import SemanticGraph
from aixl.negotiation import NegotiationOutcome
from aixl.negotiation import negotiate as _negotiate
from aixl.serialization import aixl_codec
from aixl.translators.auto import to_graph_auto as to_graph

if TYPE_CHECKING:
    from aixl.core.roundtrip import RoundTripResult
    from aixl.core.validator import ValidationResult


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
    if config is not None:
        return compare_graphs(to_graph(text_a), to_graph(text_b), config)
    from aixl.core.completeness import BOUNDARY, annotate, marker_conflicts, names_reordered
    ga, gb = annotate(to_graph(text_a), text_a), annotate(to_graph(text_b), text_b)
    res = compare_graphs(ga, gb, config)
    if res.equivalent:
        ca, cb = ga.meta['completeness'], gb.meta['completeness']
        opposed, other = marker_conflicts(set(ca['markers']), set(cb['markers']))
        lost = bool(ca['unreflected_markers'] or cb['unreflected_markers'])
        boundary = [m for m in other if any(m in pr for pr in BOUNDARY)]            # at least vs more than: inclusive vs strict bound
        if not (opposed or (other and lost) or boundary) and names_reordered(text_a, text_b):
            res.equivalent, res.verdict = False, 'INCONCLUSIVE'
            res.warnings.append({'type': 'ENTITY_ORDER_MISMATCH', 'note': 'same proper names in a different order; roles (who does what to whom) not proven equal'})
            return res
        if opposed or (other and lost) or boundary:
            res.equivalent, res.verdict = False, ('NOT_EQUIVALENT' if opposed else 'INCONCLUSIVE')
            res.warnings.append({'type': 'STRUCTURAL_MARKER_MISMATCH', 'opposed': [list(p) for p in opposed], 'other': list(other),
                                 'note': 'canonical forms agree but the texts carry different structural markers the graph does not reflect; equality not proven'})
    return res


def compare_aixl(aixl_a: str, aixl_b: str, config: dict | None = None) -> ComparisonResult:
    return compare_graphs(aixl_codec.decode(aixl_a), aixl_codec.decode(aixl_b), config)


def semantic_diff(text_a: str, text_b: str) -> str:
    return format_diff(to_graph(text_a), to_graph(text_b))


def detect_drift(source: str, target: str, config: dict | None = None) -> DriftReport:
    return detect_drift_graphs(to_graph(source), to_graph(target), config)


def detect_ambiguity(text: str, context: dict | None = None) -> AmbiguityResult:
    """`context={"entities": [{"id", "name", "aliases"?, "type"?}, ...]}` lets references be checked against known
    entities: several matches => AMBIGUOUS_REFERENCE with candidates; one => RESOLVED note; none => UNKNOWN note."""
    return detect_ambiguity_graph(text, context=context)


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


def semantic_fingerprint(text: str, config: dict | None = None, today=None) -> str:
    from aixl.core.fingerprint import fingerprint_graph
    return fingerprint_graph(to_graph(text), config, today)


def semantic_fingerprint_aixl(aixl: str, config: dict | None = None, today=None) -> str:
    from aixl.core.fingerprint import fingerprint_graph
    return fingerprint_graph(aixl_codec.decode(aixl), config, today)


def validate(text_or_graph) -> "ValidationResult":
    """VALID / INVALID / VALID_WITH_WARNINGS with structured issues (aixl/core/validator.py)."""
    from aixl.core.validator import validate_graph
    g = to_graph(text_or_graph) if isinstance(text_or_graph, str) else text_or_graph
    return validate_graph(g)


def round_trip(text_or_graph, config: dict | None = None, today=None) -> "RoundTripResult":
    """text -> graph -> AIXL -> graph -> compare; `.fidelity` is the SEMANTIC FIDELITY (aixl/core/roundtrip.py)."""
    from aixl.core.roundtrip import round_trip_graph
    g = to_graph(text_or_graph) if isinstance(text_or_graph, str) else text_or_graph
    return round_trip_graph(g, config, today)
