"""Semantic layer: fidelity between an original and a reconstructed frame (spec §24)."""
from aixl.legacy02.core.semantic_frame import SemanticFrame, FIELDS
from aixl.legacy02.core.normalizer import normalize

# critical fields (spec §25, §44): losing them can change what is done
CRITICAL = {"intent", "actions", "negations", "conditions", "references",
            "time", "confidence", "constraints", "data", "entities", "location"}
WEIGHT = {f: (2.0 if f in CRITICAL else 1.0) for f in FIELDS if f != "version"}


def _sim(a, b):
    if isinstance(a, list):
        sa = set(a) if a is not None else set()
        sb = set(b) if b is not None else set()
        if not sa and not sb:
            return 1.0
        return len(sa & sb) / len(sa | sb)
    return 1.0 if a == b else 0.0


def band(score: float) -> str:
    if score >= 1.0 - 1e-9: return "1.00 equivalencia completa"
    if score >= 0.90: return "0.90-0.99 pérdida menor"
    if score >= 0.75: return "0.75-0.89 pérdida relevante"
    if score >= 0.50: return "0.50-0.74 pérdida alta"
    return "<0.50 no confiable"


import re as _re


def _canon(v):
    """.90 == .9 (numerically equal decimals)."""
    if isinstance(v, list):
        return [_canon(x) for x in v]
    return _re.sub(r"(\.\d*?)0+(?![\d])", r"\1", v) if isinstance(v, str) else v


def fidelity(original: SemanticFrame, received: SemanticFrame) -> dict:
    """Weighted per-field score over fields present in either frame.
    Location is compared as an ordered hierarchy (VALLEDUPAR,CESAR,CO)."""
    o, r = normalize(original), normalize(received)
    num = den = 0.0
    per, critical_loss, invented = {}, [], []
    for f in WEIGHT:
        a, b = _canon(getattr(o, f)), _canon(getattr(r, f))
        if not a and not b:
            continue
        s = _sim(a, b) if f != "location" else (1.0 if a == b else 0.0)
        per[f] = round(s, 3)
        num += WEIGHT[f] * s
        den += WEIGHT[f]
        if isinstance(a, list):
            lost, extra = set(a) - set(b), set(b) - set(a)
        else:
            lost, extra = ({a} if a and a != b else set()), ({b} if b and a != b else set())
        if f in CRITICAL and lost:
            critical_loss.append({"field": f, "lost": sorted(lost)})
        if extra:
            invented.append({"field": f, "extra": sorted(extra)})
    score = round(num / den, 4) if den else 1.0
    return {"score": score, "band": band(score), "fields": per,
            "critical_loss": critical_loss, "invented": invented,
            "fields_compared": len(per)}
