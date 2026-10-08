"""AIXL v1.0 prompt §1/§5/§13/§23: token gate + verified compaction.
Compact L1 form = drop V:/I:/G: (the decoder re-derives them; verified by fingerprint equality) and abbreviate
safe tags. Output is AIXL only if (a) tokens(compact) < tokens(natural), (b) expanding + decoding the compact
form gives the SAME semantic fingerprint as the source graph, (c) no completeness/ambiguity warning.
Otherwise MODE=NATURAL. Token counting is a deterministic PROXY (no tokenizer dependency); see LIMITATIONS."""
import re

from aixl.core.completeness import is_complete
from aixl.core.fingerprint import fingerprint_graph
from aixl.serialization.aixl_codec import decode, encode
from aixl.translators.natural_to_semantic import to_graph

ABBR = {"A:TRANSLATE": "A:TRN", "A:SUMMARIZE": "A:SUM", "A:COMPARE": "A:CMP", "E:DOCUMENT": "E:DOC"}
_REV = {v: k for k, v in ABBR.items()}


def count_tokens(s: str) -> int:
    """Proxy: words/numbers/punct; long words cost ceil(len/4)."""
    n = 0
    for t in re.findall(r"\w+|[^\w\s]", s, re.UNICODE):
        n += -(-len(t) // 4) if t[0].isalnum() or t[0] == "_" else 1
    return n


def compact(wire: str) -> str:
    parts = [p for p in wire.split() if p[:2] not in ("V:", "I:", "G:")]
    return " ".join(ABBR.get(p, p) for p in parts)


def expand(c: str) -> str:
    return "V:AIXL-0.3 " + " ".join(_REV.get(p, p) for p in c.split())


def translate_gated(text: str) -> dict:
    g = to_graph(text)
    wire = encode(g)
    c = compact(wire)
    nat, aix = count_tokens(text), count_tokens(c)
    fp0 = fingerprint_graph(g)
    try:
        ok_fp = fingerprint_graph(decode(expand(c))) == fp0
    except Exception:
        ok_fp = False
    save = 1 - aix / nat if nat else 0.0
    complete = is_complete(text, g)
    has_action = bool(re.search(r"\bA:", c))
    use = ok_fp and complete and has_action and aix < nat
    reason = ("ok" if use else "incomplete_encoding" if not complete else "no_action" if not has_action
              else "fingerprint_mismatch" if not ok_fp else "no_token_saving")
    return {"mode": "AIXL" if use else "NATURAL", "output": c if use else text, "aixl": c,
            "tokens_natural": nat, "tokens_aixl": aix, "saving": round(save, 3),
            "roundtrip_fingerprint_ok": ok_fp, "complete": complete, "reason": reason, "fingerprint": fp0}
