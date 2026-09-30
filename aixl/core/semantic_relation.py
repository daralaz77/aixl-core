"""FASE 2 — SemanticRelation: a typed edge between two SemanticObjects."""
from dataclasses import dataclass, field, asdict

RELATIONS = ["TARGET", "ACTOR", "OBJECT", "SOURCE", "RESULT", "CAUSE", "CONDITION", "CONSTRAINT", "REFERENCE",
             "DEPENDS_ON", "BEFORE", "AFTER", "EQUIVALENT", "CONTRADICTS",
             # ASSUMPTION: attribute-style relations needed to hang time/location/output on an action
             "TIME", "LOCATION", "OUTPUT", "MODIFIER", "QUANTITY", "INTENT"]


@dataclass
class SemanticRelation:
    source: str
    relation: str
    target: str
    attributes: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.relation not in RELATIONS:
            raise ValueError(f"unknown relation {self.relation!r}")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SemanticRelation":
        return cls(d["source"], d["relation"], d["target"], dict(d.get("attributes", {})))
