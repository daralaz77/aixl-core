"""ADR-017 step 1 — per-side COMPLETENESS of an encoding.

A text is COMPLETE iff (a) every content word (including 1-2 character tokens and digits: 'sala B', 'Q3', '50') is accounted
for by an atom, a lexicon or an R item, and (b) every closed-class STRUCTURAL MARKER of the text (before/after, only, all,
except, not, more/less than, every ...) is reflected in the graph. Completeness is a property of ONE side; it never compares
the two texts. No tolerance parameter: any unaccounted content word or unreflected marker makes the side INCOMPLETE.
The marker lexicon is closed and small (ES/EN/PT); a language outside it yields unaccounted words, hence INCOMPLETE (safe)."""
import re

from aixl.core.normalizer import strip_accents
from aixl.core.lexicon_gaps import (FUNCTION_WORDS, _known, _forms, _TOKEN, _CONCEPT, stem)
from aixl.core.normalizer import STOP

# 1-2 character function words that are NOT content (everything else short, like 'b', 'c', 'x', is content).
# Closed-class function words of ES/EN/PT beyond the 1-2 character set (articles, contractions, pronouns, prepositions):
_CLOSED = set("""os as um uma uns umas em na nas nos no ao aos pelo pela pelos pelas dos das num numa neste nesta deste desta
 suas seus sua seu sus su mis tu tus them they their its his her our your my them these those about regarding past through
 onto upon per via than then thus also its itself themselves ellos ellas ele ela eles elas voce voces usted ustedes nosotros
 con sobre entre hacia desde hasta sin tras ante bajo segun cada algun alguna algunos algunas ningun ninguna otro otra
 which who whom whose whether either neither both such own same""".split())
SHORT_FUNCTION = set("a o e y u de en el la lo le les se me te un ya al do da ni si to of in on at as by an is it or if be we he us up so my go".split())

# class -> words/phrases (accent-stripped, lowercase, apostrophes removed). Closed list.
MARKERS = {
    "NEG": "not never no nunca nao jamais nem without sin sem prohibido prohibited forbidden proibido avoid evita evite dont doesnt cannot cant mustnt wont".split(),
    "BEFORE": "before prior antes until hasta ate".split(),
    "AFTER": "after afterwards following despues depois luego apos tras".split(),
    "ONLY": "only solely solo solamente unicamente apenas somente exclusively exclusivamente".split(),
    "ALL": "all todos todas todo toda tudo".split(),
    "EXCEPT": "except excepto exceto salvo excluding excluyendo excluindo".split(),
    "MORE": "over above greater mayor superior acima exceed minimum min".split() + ["more than", "at least", "mas de", "mais de", "al menos", "pelo menos"],
    "LESS": "under below fewer menor inferior abaixo maximum max".split() + ["less than", "at most", "up to", "menos de", "no mas de"],
    "EVERY": "every each cada daily weekly monthly yearly annually quarterly hourly diario diaria semanal mensual anual trimestral mensal diariamente semanalmente mensalmente anualmente".split(),
}
OPPOSED = [("BEFORE", "AFTER"), ("MORE", "LESS")]
_CLASS_OF = {w: c for c, ws in MARKERS.items() for w in ws if " " not in w}
_PHRASES = [(w, c) for c, ws in MARKERS.items() for w in ws if " " in w]
_ALLTOK = re.compile(r"\d+(?:[.,]\d+)?|[a-z]+")


def _norm(text: str) -> str:
    return strip_accents(str(text)).lower().replace("'", "").replace("’", "")


# A NEGATED comparator is the OPPOSITE comparator, not "NEG + comparator": 'no fewer than 3' = at least 3 (MORE), 'no more than 3' = at most 3 (LESS).
# Matched spans are consumed so neither the negation nor the comparator word is counted again (fixes 'no fewer than' read as LESS+NEG).
_NEG_COMPARATORS = [
    (re.compile(r"\b(?:no|not|nao)\s+(?:fewer|less|menos|minus)\s+(?:than\s+|de\s+|do\s+que\s+|que\s+)?"), "MORE"),
    (re.compile(r"\b(?:no|not|nao)\s+(?:more|greater|mas|mais)\s+(?:than\s+|de\s+|do\s+que\s+|que\s+)?"), "LESS"),
]


def _split_neg_comparators(s: str):
    """(classes, remaining text, consumed words) for negated comparators in normalized text `s`."""
    classes, consumed = set(), set()
    for rx, cls in _NEG_COMPARATORS:
        for m in rx.finditer(s):
            classes.add(cls); consumed |= set(_ALLTOK.findall(m.group(0)))
        s = rx.sub(" ", s)
    return classes, s, consumed


def extract_markers(text: str) -> set:
    """Closed-class structural markers present in `text` (deterministic, per text)."""
    s = _norm(text)
    neg_cls, s, _ = _split_neg_comparators(s)
    out = {c for p, c in _PHRASES if re.search(r"\b" + re.escape(p) + r"\b", s)}
    out |= {_CLASS_OF[w] for w in _ALLTOK.findall(s) if w in _CLASS_OF}
    return out | neg_cls


def marker_conflicts(ma: set, mb: set) -> tuple:
    """(opposed, other): opposed = markers that contradict each other (before vs after, more vs less) — evidence to SEPARATE;
    other = any remaining symmetric difference — evidence that equality is NOT PROVEN."""
    opposed = [(x, y) for x, y in OPPOSED if (x in ma and y in mb and x not in mb and y not in ma) or (y in ma and x in mb and y not in mb and x not in ma)]
    used = {c for p in opposed for c in p}
    other = sorted((ma ^ mb) - used)
    return opposed, other


def _evidence_tokens(graph) -> set:
    toks = set(_ALLTOK.findall(repr(graph.canonical()).lower()))
    for n in graph.by_type("RESIDUE"):
        toks |= set(_ALLTOK.findall(_norm(n.value)))
    for n in graph.by_type("CONDITION") + graph.by_type("CONSTRAINT"):
        toks |= set(_ALLTOK.findall(_norm(n.value)))
    return toks


def _reflected(cls: str, graph, ev: set) -> bool:
    c = graph.canonical()
    if any(w in ev for w in MARKERS[cls] if " " not in w) or any(all(t in ev for t in p.split()) for p in MARKERS[cls] if " " in p):
        return True
    if cls == "NEG":
        return bool(c["negation"]) or any(n.attributes.get("modality") == "FORBID" for n in graph.by_type("ACTION"))
    if cls in ("MORE", "LESS"):
        return bool(c["quantities"] or c["constraints"])
    return False


def check_completeness(text: str, graph) -> dict:
    ev = _evidence_tokens(graph)
    markers = extract_markers(text)
    unreflected = sorted(m for m in markers if not _reflected(m, graph, ev))
    skip = set(_split_neg_comparators(_norm(text))[2])
    for c in markers:
        skip |= {w for w in MARKERS[c]} | {t for p in MARKERS[c] if " " in p for t in p.split()}
    missing = []
    toks = _ALLTOK.findall(_norm(text))
    # LIMITATION (declared): verbs outside the verb table cannot be recognised; the FIRST content token of an imperative text is
    # taken as the verb the ACTION atom stands for ('mueve' -> UPDATE). Later unknown verbs stay unaccounted (safe).
    verb = next((w for w in toks if w not in FUNCTION_WORDS and w not in STOP and w not in SHORT_FUNCTION and w not in _CLOSED and not w[0].isdigit()), None) if graph.by_type("ACTION") else None
    for w in toks:
        if w == verb or w in missing or w in skip or w in FUNCTION_WORDS or w in STOP or w in SHORT_FUNCTION or w in _CLOSED:
            continue
        fs = _forms(w) | {stem(_CONCEPT.get(w, w))}
        if any((f in ev) if f[0].isdigit() else (f in ev or stem(f) in ev or _known(f)) for f in fs):
            continue
        missing.append(w)
    return {"complete": not missing and not unreflected, "unaccounted": missing, "unreflected_markers": unreflected, "markers": sorted(markers)}


def annotate(graph, text: str):
    """Attach per-side completeness + markers to graph.meta (only text-aware callers can; the Core never guesses)."""
    r = check_completeness(text, graph)
    graph.meta["completeness"] = r
    return graph
