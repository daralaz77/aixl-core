"""AIXL v1.0 prompt §1/§5/§13/§23: token gate + verified compaction.
Compact L1 form = drop V:/I:/G: (the decoder re-derives them; verified by fingerprint equality) and abbreviate
safe tags. Output is AIXL only if (a) tokens(compact) < tokens(natural), (b) expanding + decoding the compact
form gives the SAME semantic fingerprint as the source graph, (c) no completeness/ambiguity warning.
Otherwise MODE=NATURAL. Token counting is a deterministic PROXY (no tokenizer dependency); see LIMITATIONS."""
import re
from aixl.translators.natural_to_semantic import to_graph
from aixl.serialization.aixl_codec import encode, decode
from aixl.core.fingerprint import fingerprint_graph
from aixl.core.completeness import (check_completeness, _evidence_tokens, _ALLTOK, _norm, _CLOSED, SHORT_FUNCTION, MARKERS,
                                    FUNCTION_WORDS, STOP, _forms, _CONCEPT)
from aixl.core.lexicon_gaps import stem as _stem, _known
from aixl.legacy02.translators import natural_to_semantic as legacy
from aixl.core.normalizer import ALL_ACTION_RX, strip_accents

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


def strict_complete(text: str, g) -> bool:
    """check_completeness exempts the FIRST content word as 'the verb', so 'creo que ya revisa' passed with 'creo' dropped.
    Strict: the exempt verb is the word the action regex really matched; every other content word must be accounted for."""
    s = strip_accents(text.lower())
    spans = [m.span() for _, rx in ALL_ACTION_RX for m in re.finditer(rx, s)]
    if not spans:
        return False
    a, b = min(spans)
    rest = s[:a] + " " + s[b:]
    if not check_completeness("verbo " + rest, g).get("complete", False):
        return False
    # lexicon-'known' is not enough to ship in AIXL: each remaining content word must be IN the graph ('redacta el correo' -> A:GENERATE lost 'correo')
    ev = _evidence_tokens(g)
    skip = {w for ws in MARKERS.values() for p in ws for w in p.split()}
    for w in _ALLTOK.findall(_norm(rest)):
        if w in skip or w in FUNCTION_WORDS or w in STOP or w in SHORT_FUNCTION or w in _CLOSED or w[0].isdigit():
            continue
        if any(f in ev or _stem(f) in ev for f in _forms(w) | {_stem(_CONCEPT.get(w, w))}):
            continue
        # not literally in the graph: OK only if the word is a surface form of a data/entity class AND that class is in the graph
        classes = [c.lower() for c, rx in legacy.DATA_RX + legacy.ENTITY_RX if re.search(rx, w)]
        if classes and any(c in ev for c in classes):
            continue
        if not classes and _known(w) and w not in _CONCEPT:  # units, months, languages, numbers, output aliases: handled by the graph's own atoms
            continue
        return False
    return True


def translate_gated(text: str, min_sim_fp: bool = True) -> dict:
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
    comp = check_completeness(text, g)
    complete = bool(comp.get("complete", False)) and strict_complete(text, g)
    has_action = bool(re.search(r"\bA:", c))
    use = ok_fp and complete and has_action and aix < nat
    reason = ("ok" if use else "incomplete_encoding" if not complete else "no_action" if not has_action
              else "fingerprint_mismatch" if not ok_fp else "no_token_saving")
    return {"mode": "AIXL" if use else "NATURAL", "output": c if use else text, "aixl": c,
            "tokens_natural": nat, "tokens_aixl": aix, "saving": round(save, 3),
            "roundtrip_fingerprint_ok": ok_fp, "complete": complete, "reason": reason, "fingerprint": fp0}
