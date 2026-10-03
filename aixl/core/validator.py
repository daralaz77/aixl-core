"""validate_semantic_model (master prompt §43-44): structural + semantic checks on a SemanticGraph.
Returns VALID / INVALID / VALID_WITH_WARNINGS with structured issues (code, severity, node/edge, message); never a bare ERROR.
Errors make it INVALID; warnings do not. Pure function: it never modifies the graph and never executes anything."""
import re
from dataclasses import dataclass, field

from aixl.core.semantic_graph import SemanticGraph
from aixl.core.semantic_relation import RELATIONS

NODE_TYPES = {"ACTION", "ENTITY", "DATA", "TIME", "LOCATION", "CONSTRAINT", "CONDITION", "GOAL", "RESULT", "REFERENCE",
              "QUANTITY", "INTENT", "MODIFIER", "OUTPUT"}
MODALITIES = {"REQUEST", "FORBID", "ALLOW"}
PROVENANCE = {"EXPLICIT", "INFERRED", "RESOLVED", "EXTERNAL_CONTEXT", "MODEL_DERIVED"}
_ISO = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


@dataclass
class Issue:
    code: str          # INVALID_SCHEMA UNKNOWN_TYPE INVALID_RELATION MISSING_REQUIRED_FIELD CONTRADICTION INVALID_TIME INVALID_QUANTITY SEMANTIC_LOSS ...
    severity: str      # ERROR | WARNING
    where: str
    message: str

    def to_dict(self):
        return dict(code=self.code, severity=self.severity, where=self.where, message=self.message)


@dataclass
class ValidationResult:
    status: str
    issues: list = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.status != "INVALID"

    def to_dict(self):
        return dict(status=self.status, issues=[i.to_dict() for i in self.issues])


def validate_graph(g: SemanticGraph) -> ValidationResult:
    out: list[Issue] = []
    E = lambda c, w, m: out.append(Issue(c, "ERROR", w, m))
    W = lambda c, w, m: out.append(Issue(c, "WARNING", w, m))
    ids = [n.id for n in g.nodes]
    for dup in {i for i in ids if ids.count(i) > 1}:
        E("INVALID_SCHEMA", dup, "duplicate node id")
    idset = set(ids)
    for n in g.nodes:
        if n.type not in NODE_TYPES:
            E("UNKNOWN_TYPE", n.id, f"unknown node type {n.type!r}")
        if not str(n.value).strip():
            E("MISSING_REQUIRED_FIELD", n.id, "empty value")
        if not 0.0 <= n.confidence <= 1.0:
            E("INVALID_SCHEMA", n.id, "confidence outside [0,1] (it is extraction metadata, not evidence)")
        if n.provenance not in PROVENANCE:
            E("INVALID_SCHEMA", n.id, f"unknown provenance {n.provenance!r}")
        if n.type == "ACTION" and n.attributes.get("modality", "REQUEST") not in MODALITIES:
            E("INVALID_SCHEMA", n.id, f"unknown modality {n.attributes.get('modality')!r}")
        if n.type == "TIME" and not (_ISO.match(n.value) or re.fullmatch(r"[A-Z_]+", n.value) or re.search(r"[:\d]", n.value)):
            W("INVALID_TIME", n.id, f"time value {n.value!r} is neither ISO, a known token nor a clock time")
        if n.type == "TIME" and _ISO.match(n.value) and len(n.value) == 10:
            import datetime
            try:
                datetime.date.fromisoformat(n.value)
            except ValueError:
                E("INVALID_TIME", n.id, f"{n.value!r} is not a real calendar date")
        if n.type == "QUANTITY" and not re.fullmatch(r"[<>=!]*\d+(\.\d+)?", n.value):
            E("INVALID_QUANTITY", n.id, f"quantity value {n.value!r} is not numeric")
    for e in g.edges:
        w = f"{e.source}-{e.relation}->{e.target}"
        if e.relation not in RELATIONS:
            E("INVALID_RELATION", w, "unknown relation")
        for end in (e.source, e.target):
            if end not in idset:
                E("INVALID_RELATION", w, f"dangling endpoint {end!r}")
        if e.source == e.target:
            E("INVALID_RELATION", w, "self relation")
    actions = g.by_type("ACTION")
    if not actions:
        W("SEMANTIC_LOSS", "graph", "no action recognised: nothing to compare or act on (an 'equivalent' verdict here proves nothing)")
    seen: dict = {}
    for a in actions:
        seen.setdefault(a.value, set()).add(a.attributes.get("modality", "REQUEST"))
    for act, mods in seen.items():
        if {"REQUEST", "FORBID"} <= mods or {"ALLOW", "FORBID"} <= mods:
            E("CONTRADICTION", act, f"{act} is both requested/allowed and forbidden")
    for term in g.meta.get("unrecognized", []) or []:
        W("SEMANTIC_LOSS", "meta", f"term {term!r} outside the lexicon was not represented")
    for flag in g.meta.get("flags", []) or []:
        W("AMBIGUOUS_REFERENCE" if "MODALITY" not in flag else "INVALID_SCHEMA", "meta", f"flag {flag}")
    status = "INVALID" if any(i.severity == "ERROR" for i in out) else ("VALID_WITH_WARNINGS" if out else "VALID")
    return ValidationResult(status, out)
