"""FASE 2 — SemanticObject: one unit of meaning (an action, a datum, a quantity, ...)."""
from dataclasses import dataclass, field, asdict


@dataclass
class SemanticObject:
    id: str
    type: str                      # ACTION ENTITY DATA TIME LOCATION CONSTRAINT CONDITION GOAL RESULT REFERENCE QUANTITY INTENT MODIFIER OUTPUT
    value: str
    attributes: dict = field(default_factory=dict)
    confidence: float = 1.0        # confidence of EXTRACTION/normalization, NOT truth of the statement
    source: str = "natural_language"
    provenance: str = "EXPLICIT"   # EXPLICIT | INFERRED | RESOLVED | EXTERNAL_CONTEXT | MODEL_DERIVED (§68); never mixes inference with the text

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SemanticObject":
        return cls(id=d["id"], type=d["type"], value=d["value"], attributes=dict(d.get("attributes", {})),
                   confidence=float(d.get("confidence", 1.0)), source=d.get("source", "natural_language"),
                   provenance=d.get("provenance", "EXPLICIT"))
