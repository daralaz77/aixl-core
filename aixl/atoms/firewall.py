"""Semantic firewall + capability handshake + concept alignment + graph diff (master prompt §18-23, §38-43, §51).
Nothing here guesses: an unsupported concept is reported as UNSUPPORTED_CONCEPT, never mapped to a near one."""
from dataclasses import dataclass, field
from aixl.atoms import registry as R
from aixl.atoms.schema import AtomGraph
from aixl.atoms.wire import decode, DecodeError, encode


@dataclass
class Profile:
    """What one agent says it understands (AIXL HELLO)."""
    name: str
    registry_version: str = R.REGISTRY_VERSION
    atom_types: frozenset = frozenset(R.ATOM_TYPES)
    relations: frozenset = frozenset(R.RELATIONS)
    concepts: frozenset = frozenset(c["id"] for c in R.CONCEPTS)
    accept_extensions: bool = False          # may it accept `x:` concepts it does not know?
    extensions: frozenset = frozenset()      # specific x: ids it does know
    languages: frozenset = frozenset({"es", "en", "pt"})
    max_atoms: int = 200

    def hello(self) -> dict:
        return dict(aixl="0.4", name=self.name, registry=self.registry_version, atom_types=sorted(self.atom_types), relations=sorted(self.relations),
                    concepts=sorted(self.concepts), extensions=sorted(self.extensions), accept_extensions=self.accept_extensions,
                    languages=sorted(self.languages), max_atoms=self.max_atoms)

    @classmethod
    def from_hello(cls, h: dict) -> "Profile":
        return cls(h["name"], h["registry"], frozenset(h["atom_types"]), frozenset(h["relations"]), frozenset(h["concepts"]),
                   h.get("accept_extensions", False), frozenset(h.get("extensions", [])), frozenset(h.get("languages", [])), h.get("max_atoms", 200))


def common_profile(a: Profile, b: Profile) -> Profile:
    """COMMON SEMANTIC PROFILE (§20): the intersection of what both sides understand."""
    return Profile(f"{a.name}&{b.name}", min(a.registry_version, b.registry_version), a.atom_types & b.atom_types, a.relations & b.relations,
                   a.concepts & b.concepts, a.accept_extensions and b.accept_extensions, a.extensions & b.extensions, a.languages & b.languages, min(a.max_atoms, b.max_atoms))


@dataclass
class Verdict:
    accepted: bool
    reasons: list = field(default_factory=list)       # machine codes
    unsupported: list = field(default_factory=list)   # [(kind, id)]
    graph: AtomGraph | None = None


def check(g: AtomGraph, profile: Profile) -> Verdict:
    """Validate a decoded graph against what the receiver supports. Fails closed."""
    reasons, unsup = [], []
    errs = g.validate()
    if errs: reasons.append("INVALID_GRAPH"); unsup += [("error", e) for e in errs]
    if len(g.atoms) > profile.max_atoms: reasons.append("GRAPH_TOO_LARGE")
    for a in g.atoms:
        if a.type not in profile.atom_types: unsup.append(("atom_type", a.type))
        if a.concept:
            if a.concept.startswith("x:"):
                if not (profile.accept_extensions or a.concept in profile.extensions): unsup.append(("extension", a.concept))
            elif a.concept not in profile.concepts: unsup.append(("concept", a.concept))
    for _, r, _ in g.relations:
        if r not in profile.relations: unsup.append(("relation", r))
    if unsup and "INVALID_GRAPH" not in reasons: reasons.append("UNSUPPORTED_CONCEPT")
    return Verdict(not reasons, reasons, sorted(set(unsup)), g)


def receive(message: str, profile: Profile) -> Verdict:
    """AIXL MESSAGE -> VALIDATE ATOMS -> RELATIONS -> CAPABILITIES -> INTEGRITY -> ACCEPT/REJECT (§42, §43)."""
    try:
        g = decode(message, strict=True)
    except (DecodeError, ValueError, KeyError, IndexError) as e:
        return Verdict(False, ["MALFORMED_MESSAGE"], [("decode", str(e))])
    v = check(g, profile)
    declared = getattr(g, "_declared_fp", None)
    if declared is None: v.reasons.append("MISSING_FINGERPRINT"); v.accepted = False
    elif g.fingerprint() != declared: v.reasons.append("SEMANTIC_INTEGRITY_FAILURE"); v.accepted = False
    return v


# ------------------------------------------------------------------ alignment (§23)
def align(a: str, b: str) -> str:
    """EXACT_MATCH | CLOSE_MATCH | BROADER | NARROWER | RELATED | INCOMPATIBLE | UNKNOWN. Never upgrades CLOSE to EXACT."""
    if a == b: return "EXACT_MATCH"
    ca, cb = R.concept(a), R.concept(b)
    if ca is None or cb is None: return "UNKNOWN"
    if ca["type"] != cb["type"]: return "INCOMPATIBLE"
    if b in ca["near"] or a in cb["near"]: return "CLOSE_MATCH"
    if ca.get("parent") == b: return "NARROWER"
    if cb.get("parent") == a: return "BROADER"
    return "RELATED" if ca["type"] == cb["type"] and ca.get("parent") and ca.get("parent") == cb.get("parent") else "INCOMPATIBLE"


# ------------------------------------------------------------------ diff (§34-39)
def diff(g1: AtomGraph, g2: AtomGraph) -> list:
    """Atom-level differences between two graphs, id-independent. Matches atoms by (type, concept) in order, then reports
    changed value / modality / polarity / scope, added and removed atoms, and relation changes between matched atoms."""
    def sig(a): return (a.type, a.concept or "")
    left, right = list(g1.atoms), list(g2.atoms)
    pairs, used = [], set()
    for a in left:                       # exact signature (incl. value) first
        for j, b in enumerate(right):
            if j in used: continue
            if sig(a) == sig(b) and a.value == b.value and (a.modality, a.polarity) == (b.modality, b.polarity) and bool(a.scope) == bool(b.scope):
                pairs.append((a, b)); used.add(j); break
    matched_l = {id(a) for a, _ in pairs}
    out = []
    rest_l = [a for a in left if id(a) not in matched_l]
    for a in rest_l:
        for j, b in enumerate(right):
            if j in used: continue
            if sig(a) == sig(b) or (a.type == b.type and a.type in ("QUANTITY", "TIME", "QUANTIFIER", "CONDITION", "NAME", "REFERENCE")):
                pairs.append((a, b)); used.add(j)
                if a.value != b.value: out.append(dict(kind="CHANGED", atom=a.type, concept=a.concept, field="value", old=a.value, new=b.value))
                if (a.modality or "DO") != (b.modality or "DO") and a.type == "ACTION": out.append(dict(kind="CHANGED", atom=a.type, concept=a.concept, field="modality", old=a.modality or "DO", new=b.modality or "DO"))
                if a.polarity != b.polarity: out.append(dict(kind="CHANGED", atom=a.type, concept=a.concept, field="polarity", old=a.polarity, new=b.polarity))
                if bool(a.scope) != bool(b.scope): out.append(dict(kind="CHANGED", atom=a.type, concept=a.concept, field="scope", old=bool(a.scope), new=bool(b.scope)))
                break
        else:
            out.append(dict(kind="REMOVED", atom=a.type, concept=a.concept, value=a.value))
    for j, b in enumerate(right):
        if j not in used: out.append(dict(kind="ADDED", atom=b.type, concept=b.concept, value=b.value))
    mp = {a.id: b.id for a, b in pairs}
    r1 = {(mp[s], r, mp[d]) for s, r, d in g1.relations if s in mp and d in mp}
    r2 = {(s, r, d) for s, r, d in g2.relations}
    for t in sorted(r1 - r2): out.append(dict(kind="RELATION_REMOVED", relation=t[1]))
    for t in sorted(r2 - r1):
        if t[0] in mp.values() and t[2] in mp.values(): out.append(dict(kind="RELATION_ADDED", relation=t[1]))
    return out
