"""Semantic layer: the SemanticFrame (spec §4)."""
from dataclasses import asdict, dataclass, field

LIST_FIELDS = ["actions", "entities", "data", "location", "constraints",
               "conditions", "references", "negations", "output", "residue"]
SCALAR_FIELDS = ["version", "intent", "time", "priority", "confidence", "goal"]
FIELDS = SCALAR_FIELDS[:2] + ["actions", "entities", "data", "time", "location",
    "constraints", "conditions", "priority", "confidence", "references",
    "negations", "goal", "output", "residue"]


@dataclass
class SemanticFrame:
    version: str = "AIXL-0.2"
    intent: str = ""
    actions: list = field(default_factory=list)
    entities: list = field(default_factory=list)
    data: list = field(default_factory=list)
    time: str = ""
    location: list = field(default_factory=list)
    constraints: list = field(default_factory=list)
    conditions: list = field(default_factory=list)
    priority: str = ""
    confidence: str = ""
    references: list = field(default_factory=list)
    negations: list = field(default_factory=list)
    goal: str = ""
    output: list = field(default_factory=list)
    residue: list = field(default_factory=list)
    # metadata, NOT part of the meaning (spec §27, §4 SOURCE/RAW)
    lang: str = ""
    source: str = ""
    raw: str = ""

    def to_dict(self, meta=False, sparse=True):
        d = asdict(self)
        if not meta:
            for k in ("lang", "source", "raw"):
                d.pop(k)
        if sparse:
            d = {k: v for k, v in d.items() if v not in ("", [], None)}
        return d

    @classmethod
    def from_dict(cls, d):
        f = cls()
        for k, v in d.items():
            if hasattr(f, k):
                setattr(f, k, list(v) if isinstance(v, (list, tuple)) else v)
        return f

    def __eq__(self, other):
        """Order matters for actions (sequence) and location (hierarchy); other lists compare as sets."""
        if not isinstance(other, SemanticFrame):
            return False
        a, b = self.to_dict(), other.to_dict()
        if a.keys() != b.keys():
            return False
        for k in a:
            if isinstance(a[k], list) and k not in ("actions", "location"):
                if sorted(a[k]) != sorted(b[k]):
                    return False
            elif a[k] != b[k]:
                return False
        return True
