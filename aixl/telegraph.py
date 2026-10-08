"""Option A (V1 audit): TELEGRAPHIC L1 form = compact AIXL with tags removed, values lowercase, decoded by a CLOSED vocabulary
taken from the ontology (not from any test corpus). Unknown word -> TelegraphError (fail closed). Validated by fingerprint round-trip."""
import re

from aixl.core.normalizer import ALL_ACTION_RX, OUTPUT_ALIASES
from aixl.gate import ABBR, expand
from aixl.legacy02.translators import natural_to_semantic as L


class TelegraphError(ValueError):
    pass


ACTS = {a for a, _ in ALL_ACTION_RX} | {v.split(":", 1)[1] for v in ABBR.values() if v.startswith("A:")}
ENTS = {a for a, _ in L.ENTITY_RX} | {"DOC"}
DATA = {a for a, _ in L.DATA_RX} | {"TOTAL_SALES"}
OUTS = set(OUTPUT_ALIASES.values()) | {"JSON", "CSV", "TABLE", "LIST", "TEXT", "CODE", "MARKDOWN", "PDF"}
ORDER = ["A", "N", "E", "D", "Y", "T", "K", "O"]


def _cls(w: str) -> str:
    u = w.upper()
    if u in ACTS: return "A"
    if u.startswith("NO_"): return "N"
    if u in ENTS: return "E"
    if u in DATA or u.startswith("TOTAL_"): return "D"
    if re.fullmatch(r"[#@].+", w): return "Y"
    if re.fullmatch(r"(?:this|last|next|prev)_[a-z]+|today|yesterday|tomorrow", w): return "T"
    if re.fullmatch(r"(?:q[1-4]-)?\d{4}(?:-\d{2}(?:-\d{2})?)?", w) or re.fullmatch(r"q[1-4]-\d{4}", w): return "T"
    if u.startswith(("QTY=", "FORBID_", "ALLOW_", "LANG=")): return "K"
    if u in OUTS: return "O"
    raise TelegraphError(f"unknown word: {w!r}")


def to_telegraph(compact_wire: str) -> str:
    out = []
    for p in compact_wire.split():
        k, _, v = p.partition(":")
        if k in ("V", "I", "G"): continue
        if k == "F": raise TelegraphError("free-text residue F: not representable")
        out += [x.lower() for x in v.split(",")]
    return " ".join(out)


def from_telegraph(t: str) -> str:
    groups = {}
    for w in t.split():
        c = _cls(w)
        groups.setdefault(c, []).append(w.upper())
    return expand(" ".join(f"{c}:{','.join(groups[c])}" for c in ORDER if c in groups))
