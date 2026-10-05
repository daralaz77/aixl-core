"""AIXL 0.4 AtomGraph: atoms + typed relations, canonical form independent of atom ids, semantic fingerprint (§3-5, §13, §43)."""
import hashlib, json
from dataclasses import dataclass, field
from aixl.atoms.registry import REGISTRY_VERSION, ATOM_TYPES, RELATIONS, RELATION_SIG, MODALITIES, POLARITIES, is_known

STATUS = ("explicit", "inferred", "ambiguous", "unsupported")
import re
TIME_RELS = ("before", "until", "at", "after", "since", "within", "every", "during")
TIME_REF_RE = re.compile(r"mon|tue|wed|thu|fri|sat|sun|today|tomorrow|yesterday|now|\d{4}-\d{2}-\d{2}|\d{4}-\d{2}|\d{4}|\d+(h|min|d|w|mo)|\d{1,2}:\d{2}|d([1-9]|[12]\d|3[01])|"
                         r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|(this|next|last)_(week|month|quarter|year|weekend)|event:[a-z0-9_]+|month_start|month_end|(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])|morning|afternoon|evening|night|dawn|noon|midnight")
OFFSET_RE = re.compile(r"\d+(h|min|d|w|mo)")


@dataclass
class Atom:
    id: str
    type: str
    concept: str | None = None          # registry id or x:<lemma>; None for QUANTITY/TIME/CONDITION/REFERENCE/NAME
    value: object = None                # QUANTITY {mode,n,unit} | QUANTIFIER str | TIME {rel,ref} | CONDITION kind | REFERENCE kind | NAME str
    modality: str | None = None         # ACTION only (default DO)
    polarity: str = "+"                 # '-' = negated state/entity inside a condition body
    scope: str | None = None            # id of the CONDITION container the atom belongs to (the 'in' of the spec)
    status: str = "explicit"
    candidates: list = field(default_factory=list)   # other readings (AMBIGUOUS)
    span: str | None = None             # source text (provenance only; never in the fingerprint)
    extra: dict = field(default_factory=dict)   # unknown keys found when loading: never silently dropped, reported by validate()

    def to_dict(self):
        d = dict(id=self.id, type=self.type)
        for k in ("concept", "value", "scope", "span"):
            if getattr(self, k) is not None: d[k] = getattr(self, k)
        if self.type == "ACTION": d["modality"] = self.modality or "DO"
        if self.polarity != "+": d["polarity"] = self.polarity
        if self.status != "explicit": d["status"] = self.status
        if self.candidates: d["candidates"] = self.candidates
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(id=d["id"], type=d["type"], concept=d.get("concept"), value=d.get("value"), modality=d.get("modality"),
                   polarity=d.get("polarity", "+"), scope=d.get("scope"), status=d.get("status", "explicit"),
                   candidates=list(d.get("candidates", [])), span=d.get("span"),
                   extra={k: v for k, v in d.items() if k not in _ATOM_KEYS})


_ATOM_KEYS = {"id", "type", "concept", "value", "modality", "polarity", "scope", "status", "candidates", "span"}


def _val(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=True) if v is not None else ""


@dataclass
class AtomGraph:
    atoms: list = field(default_factory=list)
    relations: list = field(default_factory=list)       # (src_id, REL, dst_id)
    text: str = ""
    lang: str = ""
    registry_version: str = REGISTRY_VERSION
    unrepresented: list = field(default_factory=list)   # source fragments the producer could NOT place in atoms (explicit loss marker, never silent)

    @property
    def complete(self) -> bool:
        return not self.unrepresented

    def by_id(self):
        return {a.id: a for a in self.atoms}

    def to_dict(self):
        d = dict(registry=self.registry_version, text=self.text, lang=self.lang, atoms=[a.to_dict() for a in self.atoms],
                 relations=[list(r) for r in self.relations])
        if self.unrepresented: d["unrepresented"] = list(self.unrepresented)
        return d

    @classmethod
    def from_dict(cls, d):
        return cls([Atom.from_dict(a) for a in d.get("atoms", [])], [tuple(r) for r in d.get("relations", [])], d.get("text", ""), d.get("lang", ""), d.get("registry", REGISTRY_VERSION), list(d.get("unrepresented", [])))

    # ---- validation (semantic firewall layer 1) ----
    def validate(self):
        errs, ids = [], {}
        for a in self.atoms:
            if a.id in ids: errs.append(f"duplicate id {a.id}")
            ids[a.id] = a
            if a.type not in ATOM_TYPES: errs.append(f"{a.id}: unknown type {a.type}")
            if a.type == "ACTION" and (a.modality or "DO") not in MODALITIES: errs.append(f"{a.id}: bad modality {a.modality}")
            if a.polarity not in POLARITIES: errs.append(f"{a.id}: bad polarity")
            if a.concept is not None and not is_known(a.concept): errs.append(f"{a.id}: unregistered concept {a.concept} (use x:<lemma>)")
            if a.status not in STATUS: errs.append(f"{a.id}: bad status")
            if a.extra: errs.append(f"{a.id}: unknown atom keys {sorted(a.extra)}")
            if a.type in ("ACTION", "ENTITY", "PROPERTY", "FORMAT") and not a.concept: errs.append(f"{a.id}: {a.type} needs a concept")
            if a.type == "QUANTITY" and not (isinstance(a.value, dict) and {"mode", "n", "unit"} <= set(a.value)): errs.append(f"{a.id}: QUANTITY needs mode/n/unit")
            if a.type == "TIME":
                if not (isinstance(a.value, dict) and {"rel", "ref"} <= set(a.value)): errs.append(f"{a.id}: TIME needs rel/ref")
                elif a.value["rel"] not in TIME_RELS: errs.append(f"{a.id}: bad TIME rel {a.value['rel']}")
                elif not TIME_REF_RE.fullmatch(str(a.value["ref"])): errs.append(f"{a.id}: bad TIME ref {a.value['ref']!r}")
                elif "offset" in a.value and not OFFSET_RE.fullmatch(str(a.value["offset"])): errs.append(f"{a.id}: bad TIME offset {a.value['offset']!r}")
        for s, r, d in self.relations:
            if r not in RELATIONS: errs.append(f"unknown relation {r}")
            if s not in ids or d not in ids: errs.append(f"relation {s}-{r}->{d} dangling")
            elif r in RELATION_SIG:
                ok_s, ok_d = RELATION_SIG[r]
                if ids[s].type not in ok_s or ids[d].type not in ok_d: errs.append(f"relation {s}-{r}->{d}: {ids[s].type}->{ids[d].type} not allowed")
        for a in self.atoms:
            if a.scope and (a.scope not in ids or ids[a.scope].type != "CONDITION"): errs.append(f"{a.id}: scope {a.scope} is not a CONDITION")
        return errs

    # ---- canonical form: Weisfeiler-Lehman labels, id-independent, 3 refinement rounds ----
    def _base_label(self, a, ids):
        scope = ids[a.scope] if a.scope else None
        return "|".join([a.type, a.concept or "", _val(a.value), (a.modality or "DO") if a.type == "ACTION" else "", a.polarity,
                         ("in:" + (scope.type + _val(scope.value))) if scope else ""])

    def labels(self, rounds=3):
        ids = self.by_id()
        lab = {a.id: self._base_label(a, ids) for a in self.atoms}
        for _ in range(rounds):
            new = {}
            for a in self.atoms:
                out = sorted(f"{r}>{lab[d]}" for s, r, d in self.relations if s == a.id and d in lab)
                inn = sorted(f"{r}<{lab[s]}" for s, r, d in self.relations if d == a.id and s in lab)
                scope_l = lab[a.scope] if a.scope in lab else ""
                new[a.id] = hashlib.sha256(("#".join([lab[a.id], ";".join(out), ";".join(inn), scope_l])).encode()).hexdigest()[:16]
            lab = new
        return lab

    def canonical(self, include_unrepresented=True):
        lab = self.labels()
        ids = self.by_id()
        atoms = sorted(lab.values())
        rels = sorted(f"{lab[s]}-{r}->{lab[d]}" for s, r, d in self.relations if s in lab and d in lab)
        d = dict(v=self.registry_version, atoms=atoms, relations=rels)
        if include_unrepresented: d["unrepresented"] = sorted(self.unrepresented)
        return d

    def fingerprint(self, length=16, include_unrepresented=True):
        blob = json.dumps(self.canonical(include_unrepresented), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:length]

    def triples(self):
        """Readable id-independent relation list: (src_sig, REL, dst_sig)."""
        ids = self.by_id()
        sig = {i: self._base_label(a, ids) for i, a in ids.items()}
        return sorted((sig[s], r, sig[d]) for s, r, d in self.relations if s in sig and d in sig)
