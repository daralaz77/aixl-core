"""Semantic layer: normalization of frames (spec §8-§13, §28)."""
import re
from aixl.legacy02.core.semantic_frame import SemanticFrame, LIST_FIELDS

_LEAD0 = re.compile(r"(?<![\d.])0\.(\d)")


def norm_decimal(s: str) -> str:
    """0.90 -> .90 (never 0.80 -> 80)."""
    return _LEAD0.sub(r".\1", s)


def _is_conf_expr(s: str) -> bool:
    return bool(re.match(r"^(H|CONF\w*|CONFIDENCE)\s*[<>=!]", s))


def _dedupe(xs):
    seen, out = set(), []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def normalize(frame: SemanticFrame) -> SemanticFrame:
    f = SemanticFrame.from_dict(frame.to_dict(meta=True, sparse=False))
    f.version = f.version or "AIXL-0.2"
    for k in ("intent", "goal", "priority"):
        setattr(f, k, getattr(f, k).strip().upper())
    f.time = f.time.strip().upper() if not re.match(r'^".*"$', f.time) else f.time
    f.confidence = norm_decimal(f.confidence.strip().replace(" ", ""))
    for k in LIST_FIELDS:
        vals = [str(x).strip() for x in getattr(f, k) if str(x).strip()]
        if k in ("actions", "entities", "negations", "output"):
            vals = [v.upper() for v in vals]
        if k == "data":   # lexicon codes are UPPERCASE identifiers; anything else is a literal, kept verbatim
            vals = [v.upper() if re.fullmatch(r"[A-Za-z_]+", v) and v.upper() == v.upper().replace(" ", "") and v.isupper() else v
                    for v in vals]
        if k in ("constraints", "conditions"):
            vals = [norm_decimal(v) if (_is_conf_expr(v) or k == "constraints" and "CONF" in v.upper()) else v
                    for v in vals]
        if k != "location":            # location is hierarchical: order+repeats matter
            vals = _dedupe(vals)
        else:
            vals = [v.upper() for v in vals]
        setattr(f, k, vals)
    return f


def quarter(n: int, year=None) -> str:
    return f"Q{n}-{year}" if year else f"Q{n}"
