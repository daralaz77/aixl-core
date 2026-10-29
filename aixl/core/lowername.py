"""Candidate detectors for a person's first name written in LOWERCASE (`manda el informe a lucia`). Evaluated, not assumed: benchmarks/names_lower_eval.py.
Why `invariants.extract` does not see them: NAME recognises capitalised tokens (not at a sentence start), @handles, #ids, e-mails and URLs. Without a capital letter `ana` is
indistinguishable from `casa` unless something else says it is a name: position (after a recipient preposition) and/or a list of given names. Each is a CANDIDATE. STATUS (2026-10-29): NONE IS WIRED into the product — all were measured and rejected (LIMITATIONS.md E-HANDOFF-NAMES); kept only so benchmarks/names_lower_eval.py and
benchmarks/recipients_eval.py can be re-run."""
import os
import re

from aixl.core.normalizer import strip_accents

_PREP = frozenset("a ao to para pra pro with con com from de del ask tell ping cc cc'd".split())
_STOP = frozenset(("el la los las un una unos unas o os as um uma uns umas the a an his her its their my your our this that these those mi tu su nuestro nuestra "
                   "me te se lo le les nos you it them us him he she they ellos ellas ele ela todos todas all each cada any some "
                   "mañana manana hoy ayer ahora ya luego despues antes pronto hoje amanha ontem agora depois today tomorrow yesterday now later soon next last "
                   "si no y e and or but que como cuando donde quando onde que").split())
_WORD = re.compile(r"[a-z]+")
_GAZ = None


def gazetteer() -> frozenset:
    global _GAZ
    if _GAZ is None:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "given_names_v1.txt")
        _GAZ = frozenset(w.strip() for w in open(p, encoding="utf-8") if w.strip())
    return _GAZ


def _tokens(text: str):
    return _WORD.findall(strip_accents(text).lower())


def by_gazetteer(text: str) -> frozenset:
    g = gazetteer()
    return frozenset(t for t in _tokens(text) if t in g)


def by_position(text: str, known: frozenset = frozenset()) -> frozenset:
    """The word right after a recipient preposition (and optional article) that is not a stop word, a number or a word in `known`."""
    toks = _tokens(text)
    out = set()
    for i, t in enumerate(toks[:-1]):
        if t in _PREP:
            j = i + 1
            if toks[j] in ("el", "la", "los", "las", "al", "the", "o", "a"):
                continue                                           # an article: a common noun follows, not a bare first name
            w = toks[j]
            if len(w) >= 3 and w not in _STOP and w not in known and not w.isdigit():
                out.add(w)
    return frozenset(out)


def hybrid(text: str, known: frozenset = frozenset()) -> frozenset:
    """A gazetteer hit anywhere, or a position hit that is ALSO unknown to the gazetteer-free `known` vocabulary only when it is not a plain noun... (see the eval for what it costs)."""
    return by_gazetteer(text) | by_position(text, known)


_PREP_R = frozenset("a ao to para pra pro with con com al ask tell ping cc".split())
_ART = frozenset("el la los las un una o os as um uma the a an al".split())
_NOT_RECIPIENT = frozenset((
    "lunes martes miercoles jueves viernes sabado domingo monday tuesday wednesday thursday friday saturday sunday segunda terca quarta quinta sexta "
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre january february april june july august september october november december "
    "janeiro fevereiro marco maio junho julho setembro outubro novembro dezembro "
    "manana hoy ayer ahora ya luego despues antes pronto hoje amanha ontem agora depois today tomorrow yesterday tonight now later soon next last this "
    "mediodia medianoche noon midnight tarde noche manha noite mes ano semana dia hora minuto semana week month year day hour minute "
    "proximo proxima siguiente seguinte next primer primera segundo segunda tercer tercero ultimo ultima fin final end").split())


def recipients(text: str) -> frozenset:
    """Candidate RECIPIENTS: a capitalised/@/#/e-mail name (see `invariants`), or the word after a recipient preposition (skipping one article) that is not a date/time/number word.
    A department, a role and a person all count: for a hand-off the question is `is a recipient given?`, not `is it a person's name?`."""
    toks = _tokens(text)
    out = set()
    for i, t in enumerate(toks[:-1]):
        if t not in _PREP_R:
            continue
        j = i + 1
        if toks[j] in _ART and j + 1 < len(toks):
            j += 1
        w = toks[j]
        infinitive = t in ("para", "pra") and len(w) > 4 and w.endswith(("ar", "er", "ir"))   # `para confirmar`: a verb, not a recipient. Only after para/pra: `a wagner`, `ao javier` are names. English `to review` is NOT caught: known limit
        if len(w) >= 3 and w not in _STOP and w not in _NOT_RECIPIENT and not infinitive and not w.isdigit() and not re.fullmatch(r"\d+(?:am|pm|h|hs)?", w):
            out.add(w)
    return frozenset(out)
