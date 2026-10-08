"""FASE 10 — ContradictionDetector: explicit semantic OPPOSITION about the same object.

Never "the texts differ" => contradiction. Requires (1) the same object (overlap test) and (2) a demonstrable
opposition: request vs prohibition of the same action, allow vs forbid, enable/disable, include/exclude,
public/private, before/after the same moment."""
from dataclasses import dataclass, field

from aixl.core.ontology import ANTONYM_ACTIONS
from aixl.core.semantic_graph import SemanticGraph


@dataclass
class Alert:
    type: str
    detail: str

    def to_dict(self):
        return dict(type=self.type, detail=self.detail)


@dataclass
class ContradictionResult:
    contradiction: bool
    alerts: list = field(default_factory=list)

    def to_dict(self):
        return dict(contradiction=self.contradiction, alerts=[a.to_dict() for a in self.alerts])


def _actions(g: SemanticGraph):
    return {n.value: n.attributes.get("modality", "REQUEST") for n in g.by_type("ACTION")}


def overlapping(ga: SemanticGraph, gb: SemanticGraph) -> bool:
    """Same object? Each kind of identifier that BOTH sides state must intersect (refs/names, data, entities, period)."""
    A, B = ga.canonical(), gb.canonical()
    strip = lambda t: {x.split("(")[-1].rstrip(")") for x in t}
    for kind in ("references", "data", "entities", "time"):
        a, b = set(strip(A[kind])) if kind in ("data",) else set(A[kind]), set(strip(B[kind])) if kind in ("data",) else set(B[kind])
        if a and b and not a & b:
            return False
    return True


def detect_contradiction_graphs(ga: SemanticGraph, gb: SemanticGraph) -> ContradictionResult:
    if not overlapping(ga, gb):
        return ContradictionResult(False)
    alerts = []
    A, B = _actions(ga), _actions(gb)
    for act in set(A) & set(B):
        ma, mb = A[act], B[act]
        if {ma, mb} == {"REQUEST", "FORBID"}:
            alerts.append(Alert(f"{act}_VS_FORBID_{act}", f"one text requests {act}, the other forbids it"))
        elif {ma, mb} == {"ALLOW", "FORBID"}:
            alerts.append(Alert("ALLOW_VS_FORBID", f"{act}: allowed in one text, forbidden in the other"))
    for x, y in ANTONYM_ACTIONS:
        if (A.get(x) == "REQUEST" and B.get(y) == "REQUEST") or (A.get(y) == "REQUEST" and B.get(x) == "REQUEST"):
            alerts.append(Alert(f"{x}_VS_{y}", f"opposite actions {x}/{y} on the same object"))
    ta = [n.value for n in sorted(ga.by_type("ACTION"), key=lambda x: x.attributes.get("order", 0))]
    tb = [n.value for n in sorted(gb.by_type("ACTION"), key=lambda x: x.attributes.get("order", 0))]
    if ga.meta.get("ordered") and gb.meta.get("ordered") and len(ta) > 1 and sorted(ta) == sorted(tb) and ta == tb[::-1]:
        alerts.append(Alert("BEFORE_VS_AFTER", f"steps in opposite order: {'>'.join(ta)} vs {'>'.join(tb)}"))
    ca, cb = {n.value for n in ga.by_type("CONSTRAINT")}, {n.value for n in gb.by_type("CONSTRAINT")}
    if ("VISIBILITY=PUBLIC" in ca and "VISIBILITY=PRIVATE" in cb) or ("VISIBILITY=PRIVATE" in ca and "VISIBILITY=PUBLIC" in cb):
        alerts.append(Alert("PUBLIC_VS_PRIVATE", "visibility PUBLIC vs PRIVATE"))
    for c in ca:
        if c.startswith("BEFORE=") and "AFTER=" + c[7:] in cb or c.startswith("AFTER=") and "BEFORE=" + c[6:] in cb:
            alerts.append(Alert("BEFORE_VS_AFTER", f"{c} vs the opposite bound on the same moment"))
    return ContradictionResult(bool(alerts), alerts)
