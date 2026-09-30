"""Semantic layer: the 10 pre-emit checks (spec §34)."""
import re
from aixl.legacy02.core.semantic_frame import SemanticFrame
from aixl.legacy02.core.encoder import encode
from aixl.legacy02.core.parser import parse, AixlError
from aixl.legacy02.core.normalizer import normalize, norm_decimal
from aixl.legacy02.protocol.atoms import INTENTS, ACTIONS
from aixl.legacy02.protocol.versions import check_version

NEG_CUE = re.compile(r"\b(no|nunca|jam[aá]s|sin|don'?t|do not|never|not|n[aã]o|without)\b", re.I)
COND_CUE = re.compile(r"\b(si|if|when|cuando|se|caso|siempre que|unless|a menos que)\b", re.I)
NUM = re.compile(r"(?<![\w#-])\d+(?:[.,]\d+)?")


def validate(frame: SemanticFrame, raw: str = "") -> list:
    f = normalize(frame)
    aixl = encode(f)
    raw = raw or frame.raw or ""
    res = []

    def chk(n, name, ok, detail=""):
        res.append({"check": n, "name": name, "ok": bool(ok), "detail": detail})

    chk(1, "version válida", check_version(f.version), f.version)
    chk(2, "intención válida", f.intent in INTENTS, f.intent)
    bad = [a for a in f.actions if a not in ACTIONS]
    chk(3, "acciones válidas", not bad, ",".join(bad))
    try:
        parse(aixl); syn = True
    except AixlError as e:
        syn = False
    chk(4, "sintaxis válida", syn)
    if raw:
        refs = re.findall(r"#\w+", raw)
        chk(5, "referencias preservadas", all(r in aixl for r in refs), ",".join(refs))
        neg_raw = bool(NEG_CUE.search(raw))
        chk(6, "negaciones preservadas", (not neg_raw) or bool(f.negations or f.constraints),
            "cue de negación en el texto" if neg_raw else "")
        chk(7, "condiciones preservadas",
            (not COND_CUE.search(raw)) or bool(f.conditions) or bool(f.confidence),
            "")
        nums = [norm_decimal(n.replace(",", ".")) for n in NUM.findall(raw)]
        miss = [n for n in nums if n not in aixl and n.lstrip(".") not in aixl]
        chk(8, "cantidades preservadas", not miss, ",".join(miss))
        yrs = re.findall(r"\b(?:19|20)\d\d(?:-\d\d(?:-\d\d)?)?\b", raw)
        chk(9, "fechas preservadas", all(y in aixl for y in yrs), ",".join(y for y in yrs if y not in aixl))
    else:
        for n, nm in ((5, "referencias preservadas"), (6, "negaciones preservadas"),
                      (7, "condiciones preservadas"), (8, "cantidades preservadas"),
                      (9, "fechas preservadas")):
            chk(n, nm, True, "sin RAW: no verificable")
    try:
        chk(10, "reconstrucción consistente", parse(aixl) == f)
    except AixlError:
        chk(10, "reconstrucción consistente", False)
    return res


def errors_of(results):
    codes = []
    for r in results:
        if not r["ok"]:
            codes.append({1: "VERSION_MISMATCH", 4: "INVALID_AIXL"}.get(r["check"], "SEMANTIC_LOSS"))
    return sorted(set(codes))
