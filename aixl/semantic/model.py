"""0.3-R semantic model (master prompt §5-8, §20, §24).

Atom        one typed unit of meaning: type, value, source span, provenance (EXPLICIT / INFERRED / DEFAULTED / ASSUMED),
            scope (index of the step it belongs to) and `candidates` = OTHER readings the text allows. A non-empty
            `candidates` IS the AMBIGUOUS state: the parser never picks one reading as the truth.
Step        one action with its own atoms. Steps are ordered; `order` says whether the ORDER is part of the meaning:
            'explicit' (then/before/after/first), 'implicit' (plain 'and' between verbs) or None (single step).
Field states (§6) are explicit, never conflated: an absent atom type means ABSENT/UNSPECIFIED (the text does not say);
            AMBIGUOUS = atom with candidates; CONFLICTING = a `flags` entry; UNKNOWN is never defaulted into a value.
"""
from dataclasses import dataclass, field

PROVENANCE = ("EXPLICIT", "INFERRED", "DEFAULTED", "ASSUMED")
DIFF_TYPES = ("LOSS", "DISTORTION", "ADDITION", "SUBSTITUTION", "CONTRADICTION")


@dataclass(frozen=True)
class Atom:
    type: str
    value: object
    span: tuple = (0, 0)
    provenance: str = "EXPLICIT"
    scope: int = 0
    confidence: float = 1.0
    candidates: frozenset = frozenset()

    @property
    def alternatives(self) -> frozenset:
        return frozenset({self.value}) | self.candidates

    @property
    def ambiguous(self) -> bool:
        return bool(self.candidates)

    def to_dict(self) -> dict:
        d = dict(type=self.type, value=self.value if not isinstance(self.value, (set, frozenset)) else sorted(map(str, self.value)),
                 span=list(self.span), provenance=self.provenance, scope=self.scope, confidence=self.confidence)
        if self.candidates:
            d["status"] = "AMBIGUOUS"
            d["candidates"] = sorted(map(str, self.candidates))
        return d


@dataclass
class Step:
    idx: int
    atoms: list = field(default_factory=list)
    items: list = field(default_factory=list)       # ordered (kind, key): content tokens / ordinals / names, for role-order checks
    order: str | None = None

    def get(self, type_: str) -> list:
        return [a for a in self.atoms if a.type == type_]

    def one(self, type_: str):
        got = self.get(type_)
        return got[0] if got else None


@dataclass
class SemanticObject:
    text: str
    lang: str
    steps: list
    flags: list = field(default_factory=list)       # (code, detail): UNREPRESENTABLE_* / AMBIGUOUS_* / SANITIZER findings
    norm: tuple = ()                                # normalized token tuple (identity check)

    @property
    def unrepresentable(self) -> list:
        return [f for f in self.flags if f[0].startswith("UNREPRESENTABLE")]

    def atoms(self):
        return [a for s in self.steps for a in s.atoms]

    def to_dict(self) -> dict:
        return dict(text=self.text, language=self.lang, flags=[list(f) for f in self.flags],
                    steps=[dict(index=s.idx, order=s.order, atoms=[a.to_dict() for a in s.atoms], items=[list(i) for i in s.items]) for s in self.steps])


@dataclass
class Diff:
    path: str
    type: str          # one of DIFF_TYPES
    original: object
    new: object
    severity: str      # MINOR | MODERATE | MAJOR | CRITICAL

    def to_dict(self) -> dict:
        return dict(semantic_path=self.path, difference_type=self.type, original=self.original, new=self.new, severity=self.severity)


@dataclass
class Verdict:
    verdict: str                      # EQUIVALENT | NOT_EQUIVALENT | INCONCLUSIVE
    diffs: list = field(default_factory=list)          # definitive differences (loss / distortion / addition ...)
    unresolved: list = field(default_factory=list)     # reasons the system cannot prove either way (fail-closed)
    warnings: list = field(default_factory=list)       # inferred / defaulted assumptions the verdict relied on
    flags: list = field(default_factory=list)          # parser flags raised on either text (AMBIGUOUS_* / UNREPRESENTABLE_* / SANITIZER), by code

    @property
    def equivalent(self) -> bool:
        return self.verdict == "EQUIVALENT"

    def to_dict(self) -> dict:
        return dict(verdict=self.verdict, diffs=[d.to_dict() for d in self.diffs], unresolved=self.unresolved, warnings=self.warnings, flags=self.flags)
