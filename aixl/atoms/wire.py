"""AIXL 0.4 wire format: a line-oriented, transport-independent serialization of an AtomGraph (master prompt §15, §16, §44).
decode(encode(g)) has the same fingerprint as g; decode never guesses: unknown types/relations/concepts are reported, not mapped."""
import json
from aixl.atoms.schema import Atom, AtomGraph
from aixl.atoms.registry import REGISTRY_VERSION, ATOM_TYPES, RELATIONS

MAGIC = "AIXL 0.4"


def _canon_ids(g: AtomGraph):
    """deterministic renumbering: by WL label, ties by original order. Returns {old_id: new_id}."""
    lab = g.labels()
    order = sorted(range(len(g.atoms)), key=lambda i: (lab[g.atoms[i].id], i))
    return {g.atoms[i].id: f"n{k + 1}" for k, i in enumerate(order)}, order


def _j(v):
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"), sort_keys=True).replace(" ", "\\u0020")


def encode(g: AtomGraph, with_text: bool = False) -> str:
    mp, order = _canon_ids(g)
    lines = [MAGIC, f"REG {g.registry_version}", f"FP {g.fingerprint()}"]
    if g.lang: lines.append(f"LANG {g.lang}")
    if with_text and g.text: lines.append("TXT " + _j(g.text))
    for i in order:
        a = g.atoms[i]
        parts = ["A", mp[a.id], a.type, a.concept or "-"]
        if a.type == "ACTION": parts.append("m=" + (a.modality or "DO"))
        if a.polarity != "+": parts.append("pol=" + a.polarity)
        if a.scope: parts.append("sc=" + mp[a.scope])
        if a.status != "explicit": parts.append("st=" + a.status)
        if a.candidates: parts.append("cand=" + _j(a.candidates))
        if a.value is not None: parts.append("v=" + _j(a.value))
        lines.append(" ".join(parts))
    for s, r, d in sorted(g.relations, key=lambda x: (mp[x[0]], x[1], mp[x[2]])):
        lines.append(f"R {mp[s]} {r} {mp[d]}")
    for u in sorted(g.unrepresented):
        lines.append("U " + _j(u))
    return "\n".join(lines) + "\n"


class DecodeError(ValueError):
    pass


def decode(text: str, strict: bool = True) -> AtomGraph:
    """strict: any unknown type/relation/malformed line raises DecodeError (the firewall relies on this)."""
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines or lines[0] != MAGIC: raise DecodeError("bad magic")
    g = AtomGraph(); declared_fp = None
    for l in lines[1:]:
        p = l.split(" ")
        k = p[0]
        if k == "REG": g.registry_version = p[1]
        elif k == "FP": declared_fp = p[1]
        elif k == "LANG": g.lang = p[1]
        elif k == "TXT": g.text = json.loads(l[4:])
        elif k == "A":
            if len(p) < 4: raise DecodeError(f"short atom line: {l}")
            if p[2] not in ATOM_TYPES and strict: raise DecodeError(f"unsupported atom type {p[2]}")
            a = Atom(id=p[1], type=p[2], concept=None if p[3] == "-" else p[3])
            for kv in p[4:]:
                key, _, val = kv.partition("=")
                if key == "m": a.modality = val
                elif key == "pol": a.polarity = val
                elif key == "sc": a.scope = val
                elif key == "st": a.status = val
                elif key == "cand": a.candidates = json.loads(val)
                elif key == "v": a.value = json.loads(val)
                elif strict: raise DecodeError(f"unknown atom key {key}")
            g.atoms.append(a)
        elif k == "U": g.unrepresented.append(json.loads(l[2:]))
        elif k == "R":
            if len(p) != 4: raise DecodeError(f"bad relation line: {l}")
            if p[2] not in RELATIONS and strict: raise DecodeError(f"unsupported relation {p[2]}")
            g.relations.append((p[1], p[2], p[3]))
        elif strict: raise DecodeError(f"unknown line kind {k}")
    g._declared_fp = declared_fp
    return g
