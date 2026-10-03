"""Round-trip engine (§38): text -> graph -> AIXL -> graph -> compare. SEMANTIC FIDELITY = share of canonical
dimensions preserved (1.0 = identical canonical form). It measures what the *encoding* preserves, not whether the
original extraction was right: anything the translator never extracted cannot be lost here (see LIMITATIONS)."""
from dataclasses import dataclass, field

from aixl.core.comparator import compare_graphs
from aixl.core.semantic_graph import SemanticGraph


@dataclass
class RoundTripResult:
    preserved: bool
    fidelity: float
    aixl: str
    differences: list = field(default_factory=list)
    error: str = ""

    def to_dict(self):
        return dict(preserved=self.preserved, fidelity=round(self.fidelity, 4), aixl=self.aixl,
                    differences=[d.to_dict() for d in self.differences], error=self.error)


def round_trip_graph(g: SemanticGraph, config: dict | None = None, today=None) -> RoundTripResult:
    from aixl.serialization import aixl_codec
    try:
        line = aixl_codec.encode(g)
        back = aixl_codec.decode(line)
    except Exception as ex:                      # structured, never a bare crash: a failed codec IS a fidelity loss
        return RoundTripResult(False, 0.0, "", [], f"{type(ex).__name__}: {ex}")
    r = compare_graphs(g, back, config, today)
    scored = [v for v in r.per_dimension.values() if v is not None]
    fidelity = sum(scored) / len(scored) if scored else 1.0
    return RoundTripResult(r.equivalent, fidelity, line, r.differences)
