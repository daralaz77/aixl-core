"""FASE 5 — Natural language (ES/EN/PT) -> SemanticGraph.

LANGUAGE layer only: it extracts and NORMALIZES what the text says, never what it might mean. Nothing is invented:
absent time/location/format stay empty (NOT_SPECIFIED = empty), unresolved things are flagged, not filled.
Base: the 0.2 rule-based analyzer (vendored in aixl.legacy02) + the 0.3 extensions below.
"""
import functools
import re
from datetime import date

from aixl.legacy02.translators import natural_to_semantic as legacy
from aixl.legacy02.core.semantic_frame import SemanticFrame
from aixl.legacy02.core.normalizer import normalize as _norm_frame
from aixl.legacy02.protocol.atoms import derive_intent, derive_goal
from aixl.core.normalizer import (SemanticNormalizer, EXTRA_ACTION_RX, FORBID_CUE, ALLOW_CUE, AGG_MAP, OUTPUT_ALIASES,
                                  strip_accents, UNIT_MAP, STOP)
from aixl.core.ontology import resolve_relative_time_str
from aixl.core.semantic_graph import SemanticGraph

NORM = SemanticNormalizer()


@functools.lru_cache(maxsize=1)
def _all_action_rx():
    return [(a, re.compile(rx.replace(r"\b", ""))) for a, rx in legacy.ACTION_RX + EXTRA_ACTION_RX]


def _action_of_word(w: str):
    for a, rx in _all_action_rx():
        if rx.fullmatch(w):
            return a
    return None


OP_WORDS = [
    (">=", r"al menos|at least|como minimo|minimum of|no menos de|or more|pelo menos"),
    ("<=", r"como maximo|at most|no mas de|up to|no more than"),
    (">", r"mas de|more than|over|above|mayor(?:es)? (?:que|a|de)|superior(?:es)? a|por encima de|exceed\w*|supera\w*|mais de"),
    ("<", r"menos de|fewer than|less than|below|under|menor(?:es)? (?:que|a|de)|inferior(?:es)? a|por debajo de|menos que"),
]
_OP_ALT = "|".join(rx for _, rx in OP_WORDS)
IF = r"(?:si|if|when|cuando|whenever|siempre que|cada vez que|every time|de haber|in case|caso|em caso de|en caso de|quando|se|as long as)"
EXIST_V = (r"(?:existen?|exista[n]?|hay|haya[n]?|hubiera|there\s+(?:are|is)|exist[s]?|"
           r"se\s+(?:detecta[n]?|encuentra[n]?)|is\s+detected|are\s+detected|is\s+found|are\s+found|se\s+(?:detecte[n]?|encuentre[n]?)|houver|existir|existem)")
COUNT_V = EXIST_V[:-1] + r"|tiene[n]?|tenga[n]?|has|have|contiene[n]?|contenga[n]?|contains?)"
COUNT_COND = re.compile(rf"\b{IF}\s+{COUNT_V}\s+(?:(?P<op>{_OP_ALT})\s+)?(?P<n>\d[\d.,]*)\s*(?P<unit>[a-z]+)?")
EXIST_COND = re.compile(rf"\b{IF}\s+(?:(?:el|la|los|las|the)\s+)?(?:\w+\s+){{0,2}}?(?:{EXIST_V})\s+(?:(?:una?|an?|any|alg[uú]n[a]?s?|uma?)\s+)?(?P<noun>[a-z]+)")
ASSERT = re.compile(r"\b(?P<neg>no|not|n't|nunca|never|sin|without|nao|sem)?\s*(?P<v>contenga[n]?|contiene[n]?|tenga[n]?|tiene[n]?|contains?|contain|has|have|hay)\s+(?:(?:una?|an?|any|alg[uú]n[a]?s?)\s+)?(?:\w+\s+){0,2}?(?P<noun>[a-z]+)")
MONTHS_RX = "|".join(sorted(legacy.MONTHS, key=len, reverse=True))
PART_MAP = [
    ("SEND", r"enviad[oa]s?|sent|enviado"), ("GENERATE", r"generad[oa]s?|gerad[oa]s?|generated|producid[oa]s?|written|escrit[oa]s?"),
    ("DELETE", r"eliminad[oa]s?|borrad[oa]s?|excluíd[oa]s?|excluid[oa]s?|deleted|removed|removid[oa]s?|apagad[oa]s?"),
    ("ANALYZE", r"analizad[oa]s?|analisad[oa]s?|analy[sz]ed|examinad[oa]s?|examined"),
    ("TRANSLATE", r"traducid[oa]s?|traduzid[oa]s?|translated"), ("CALCULATE", r"calculad[oa]s?|calculated|computed"),
    ("UPDATE", r"actualizad[oa]s?|atualizad[oa]s?|updated|modificad[oa]s?|modified"),
    ("CHECK", r"verificad[oa]s?|checked|verified|revisad[oa]s?"), ("VALIDATE", r"validad[oa]s?|validated"),
    ("COMPARE", r"comparad[oa]s?|compared"), ("CREATE", r"cread[oa]s?|criad[oa]s?|created"),
    ("RETRIEVE", r"recuperad[oa]s?|retrieved|fetched|obtenid[oa]s?|obtid[oa]s?"),
    ("EXECUTE", r"ejecutad[oa]s?|executad[oa]s?|executed|run"), ("GET", r"presentad[oa]s?|presented|shown|mostrad[oa]s?"),
]
PASSIVE = re.compile(r"\b(?:debe[n]?|deber[ií]a[n]?|tiene[n]?\s+que|must|should|has\s+to|have\s+to|needs?\s+to|deve[m]?|precisa[m]?)\s+(?P<neg>nunca\s+|never\s+|jam[aá]s\s+|no\s+|not\s+)?(?:ser|be)\s+(?P<part>[a-zà-ú]+)")
NEG_PASSIVE_NO = re.compile(r"\b(?:no\s+debe[n]?|must\s+not|should\s+not|nao\s+deve[m]?)\s+(?:ser|be)\s+(?P<part>[a-zà-ú]+)")
RANK_CUE = re.compile(r"\b(mas vendidos|mas vendidas|best[- ]selling|top[- ]selling|mejores|best|principales|principais|main|leading|top|mais vendidos)\b")
SELECT_RX = re.compile(r"\b(primeros|primeras|first|primeiros|primeiras|ultimos|ultimas|last|latest|ultimos)\s+(\d[\d.,]*)\b")
TIME_UNITS = {"dias", "days", "semanas", "weeks", "meses", "months", "anos", "years", "horas", "hours", "minutos", "minutes", "dia", "day"}
NONNAME = set(legacy.MONTHS) | set(legacy.LANGS) | {"json", "csv", "markdown", "excel", "word", "pdf", "html", "xml", "lunes", "martes", "miercoles", "jueves",
    "viernes", "sabado", "domingo", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "segunda", "terca", "quarta", "quinta",
    "sexta", "gracias", "please", "hola", "hello"} | {k.lower() for k in legacy.COUNTRIES} | {p.lower().replace("_", " ") for p in legacy.PLACES}


NUMBER_WORDS = {
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "veinte": 20, "treinta": 30,
    "cincuenta": 50, "cien": 100, "ciento": 100, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "twenty": 20, "thirty": 30, "fifty": 50, "hundred": 100, "dois": 2, "duas": 2, "quatro": 4, "sete": 7, "oito": 8,
    "dez": 10, "vinte": 20, "trinta": 30, "cinquenta": 50, "cem": 100}
LIGHT = [
    (r"(?:ejecut\w+|corre|correr|realiz\w+|haz|hacer|efectu\w+|run|runs|execute|perform|make|rode|rodar|faca)\s+(?:el|la|un|una|the|a|an|o|uma?|os|as)?\s*(?:analisis|analise|analysis)\b", "analiza"),
    (r"(?:ejecut\w+|corre|correr|realiz\w+|haz|hacer|efectu\w+|run|runs|execute|perform|make|rode|rodar|faca)\s+(?:el|la|un|una|the|a|an|o|uma?|os|as)?\s*(?:validacion|validacao|validation)\b", "valida"),
    (r"(?:ejecut\w+|corre|correr|realiz\w+|haz|hacer|efectu\w+|run|runs|execute|perform|make|rode|rodar|faca)\s+(?:el|la|un|una|the|a|an|o|uma?|os|as)?\s*(?:calculo|calculation|calcul)\b", "calcula"),
    (r"(?:ejecut\w+|corre|correr|realiz\w+|haz|hacer|efectu\w+|run|runs|execute|perform|make|rode|rodar|faca)\s+(?:el|la|un|una|the|a|an|o|uma?|os|as)?\s*(?:traduccion|traducao|translation)\b", "traduce"),
    (r"(?:ejecut\w+|corre|correr|realiz\w+|haz|hacer|efectu\w+|run|runs|execute|perform|make|rode|rodar|faca)\s+(?:el|la|un|una|the|a|an|o|uma?|os|as)?\s*(?:comparacion|comparacao|comparison)\b", "compara"),
    (r"(?:ejecut\w+|corre|correr|realiz\w+|haz|hacer|efectu\w+|run|runs|execute|perform|make|rode|rodar|faca)\s+(?:el|la|un|una|the|a|an|o|uma?|os|as)?\s*(?:verificacion|verificacao|verification)\b", "verifica"),
]


def _sub_stripped(text, pattern, repl):
    """Regex on the accent-stripped copy (length preserving), substitution applied to the original."""
    s = strip_accents(text)
    out, last = [], 0
    for m in re.finditer(pattern, s):
        out.append(text[last:m.start()]); out.append(repl); last = m.end()
    out.append(text[last:])
    return "".join(out)


def _spans(pattern, s):
    return [m.span() for m in re.finditer(pattern, s)]


def _mask(s, spans):
    chars = list(s)
    for a, b in spans:
        for i in range(a, b):
            chars[i] = " "
    return "".join(chars)


def _fold_inflections(text: str) -> str:
    """Rewrite inflected verb forms to the base form the lexicon knows: English -ing/-ed, ES/PT enclitic pronouns."""
    def rep(m):
        w = m.group(0)
        lw = strip_accents(w)
        if _action_of_word(lw):
            return w
        if lw.endswith("ing") and len(lw) > 5:
            for cand in (lw[:-3], lw[:-3] + "e", lw[:-4]):
                if _action_of_word(cand):
                    return cand
        if lw.endswith("ed") and len(lw) > 4:
            for cand in (lw[:-2], lw[:-1], lw[:-3]):
                if _action_of_word(cand):
                    return cand
        if lw.endswith(("en", "an")) and len(lw) > 4 and _action_of_word(lw[:-1]) and not _action_of_word(lw):
            return lw[:-1]
        m2 = re.fullmatch(r"([a-z]{3,}?)-?(lo|la|los|las|le|les|me|se)", lw)
        if m2 and _action_of_word(m2.group(1)):
            return m2.group(1)
        return w
    return re.sub(r"[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ]+)?", lambda m: rep(m) if "-" not in m.group(0) else rep(re.match(r"[^-]*-[^-]*", m.group(0))), text)


def _preprocess(text: str) -> str:
    t = text.replace("’", "'")
    for rx, verb in LIGHT:                                   # "ejecuta el análisis" == "analiza"
        t = _sub_stripped(t, rx, verb)
    t = re.sub(r"\b([A-Za-zÀ-ÿ]+)\b", lambda m: str(NUMBER_WORDS[strip_accents(m.group(1))]) if strip_accents(m.group(1)) in NUMBER_WORDS else m.group(0), t)
    t = re.sub(r"\b((?:19|20)\d\d)[\s-]*[Qq]([1-4])\b", r"Q\2 \1", t)
    t = re.sub(r"\b([1-4])\s*[Tt](?:rim)?\.?\s*((?:19|20)\d\d)\b", r"Q\1 \2", t)
    t = re.sub(r"\b[Qq]([1-4])\s+of\s+((?:19|20)\d\d)", r"Q\1 \2", t)
    return t


def _cond_clauses(t: str):
    """Extract structured conditions and remove their clauses from the text given to the 0.2 analyzer."""
    s = strip_accents(t)
    conds = []
    m = COUNT_COND.search(s)
    if m:
        op = "="
        if m.group("op"):
            for o, rx in OP_WORDS:
                if re.fullmatch(rx, m.group("op")):
                    op = o
                    break
        n = NORM.normalize_number(m.group("n").rstrip(".,"))
        unit = NORM.normalize_unit(m.group("unit") or "")
        conds.append(f"COUNT{op}{n}" + (f":{unit}" if unit else ""))
        t, s = t[:m.start()] + " " + t[m.end():], s[:m.start()] + " " + s[m.end():]
    else:
        m = EXIST_COND.search(s)
        if m:
            noun = m.group("noun")
            code = next((c for c, rx in legacy.DATA_RX + legacy.ENTITY_RX if re.fullmatch(rx.replace(r"\b", ""), noun)), None)
            if code:
                conds.append(f"{code}_EXISTS")
                t, s = t[:m.start()] + " " + t[m.end():], s[:m.start()] + " " + s[m.end():]
    return t, conds


def _assertions(t: str):
    s = strip_accents(t)
    conds, spans = [], []
    for m in ASSERT.finditer(s):
        noun = m.group("noun")
        code = next((c for c, rx in legacy.DATA_RX + legacy.ENTITY_RX if re.fullmatch(rx.replace(r"\b", ""), noun)), None)
        if code:
            conds.append(("NOT_" if m.group("neg") else "") + f"CONTAINS:{code}")
            spans.append((m.start(), m.start("noun")))
    return conds, spans


def _passive(t: str):
    s = strip_accents(t)
    out, spans = [], []
    for m in list(PASSIVE.finditer(s)) + list(NEG_PASSIVE_NO.finditer(s)):
        part = m.group("part")
        act = next((a for a, rx in PART_MAP if re.fullmatch(rx, part)), None)
        if act:
            neg = bool(m.groupdict().get("neg") and re.match(r"(?:nunca|never|jamas|no|not)", m.group("neg").strip())) or m.re is NEG_PASSIVE_NO
            out.append((m.start(), act, neg))
            spans.append(m.span())
    return out, spans


def _names(text: str, frame: SemanticFrame):
    """Quoted strings and capitalized proper names (recipients, projects...) as REFERENCES, never guessed."""
    out = []
    for m in re.finditer(r"(?<![\w])'([^']{2,40})'(?![\w])|\"([^\"]{2,40})\"|«([^»]{2,40})»|“([^”]{2,40})”", text):
        out.append("@" + next(g for g in m.groups() if g).strip().upper())
    loc = {x.lower() for x in frame.location}
    for m in re.finditer(r"(?<![\w'])([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})\b", text):
        w = m.group(1)
        before = text[:m.start()].rstrip()
        if not before or before[-1] in ".!?¿¡:;\n" or before.endswith(("\"", "'", "(")):
            continue                                  # sentence-initial capital = ordinary word
        lw = strip_accents(w)
        if lw in NONNAME or lw in loc or _action_of_word(lw) or lw in UNIT_MAP:
            continue
        if any(re.fullmatch(rx.replace(r"\b", ""), lw) for _c, rx in legacy.DATA_RX + legacy.ENTITY_RX):
            continue
        out.append("@" + w.upper())
    return list(dict.fromkeys(out))


def _quantities(pre: str, frame: SemanticFrame):
    s = strip_accents(pre)
    spans = []
    spans += _spans(r"#\w+", s)
    spans += _spans(r"\b\d{4}-\d{2}(?:-\d{2})?\b", s)
    spans += _spans(r"\b\d{1,2}:\d{2}\s*(?:a\.?m\.?|p\.?m\.?)?\b", s)
    spans += _spans(r"\bq[1-4]\b(?:[\s-]*(?:of|de|del|in)?\s*(?:19|20)\d\d)?", s)
    spans += _spans(r"\b[1-4](?:st|nd|rd|th|er|ro|do|to|o)?\s+(?:trimestre|quarter)\b", s)
    spans += _spans(rf"\b\d{{1,2}}\s+(?:de\s+)?(?:{MONTHS_RX})\b(?:\s*(?:de\s+|,\s*)?(?:19|20)\d\d)?", s)
    spans += _spans(rf"\b(?:{MONTHS_RX})\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+(?:19|20)\d\d\b", s)
    spans += _spans(r"\b\d{1,2}/\d{1,2}/(?:19|20)\d\d\b", s)                                                             # DD/MM/YYYY (0.3)
    spans += _spans(rf"\b\d{{1,2}}\s+(?:y|al|a|and|to)\s+(?:el\s+)?\d{{1,2}}\s+(?:de\s+)?(?:{MONTHS_RX})\s*(?:de\s+)?(?:19|20)\d\d\b", s)  # 'del 1 al 15 de agosto de 2026' (0.3)
    for y in re.findall(r"(?:19|20)\d\d", frame.time or ""):
        spans += _spans(rf"\b{y}\b", s)
    spans += _spans(r"\b(?:confianza|confidence|confianca|certeza|certainty)\b[^0-9;]{0,40}?\d+(?:[.,]\d+)?\s*%?", s)
    spans += _spans(r"\d+(?:[.,]\d+)?\s*%\s*(?:de\s+|of\s+)?(?:confianza|confidence|confianca)", s)
    spans += _spans(r"\d*[.,]?\d+\s+(?:de\s+)?(?:confidence|confianza|confianca)\b", s)
    spans += _spans(r"\b(?:maximo(?: de)?|max|maximum(?: of)?|a maximum of|at most|up to|hasta|ate|no maximo|limit(?:e|ed)?\s*(?:de|to|of)?|limita\w*\s+a|top|no more than|no mas de|como maximo|aproximadamente|approximately|approx\.?|about|around|cerca de|alrededor de|roughly|at the most)\s+\d[\d.,]*", s)
    spans += _spans(r"\b(?:older|newer) than\s+\d+\s+(?:anos?|years?|meses?|months?|dias?|days?)\b", s)               # AGE, not a quantity (0.3)
    spans += _spans(r"\b(?:mas|menos) de\s+\d+\s+(?:anos?|meses?|dias?)\s+de\s+antiguedad\b", s)                       # AGE, not a quantity (0.3)
    spans += _spans(r"\b(?:ticket|issue|caso|case|reporte|report|evento|event|documento|document|informe|solicitud|request|numero|n[uú]mero|number|no\.?|num\.?)\s+(?:numero|n[uú]mero|number|no\.?|num\.?)?\s*#?\d+\b", s)  # REFERENCE, not a quantity (0.3)
    m = _mask(s, spans)
    out = []
    for mt in re.finditer(r"(?<![\w.,-])(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)(\s*%)?(?![\w-])", m):
        num = NORM.normalize_number(mt.group(1))
        if mt.group(2):
            unit = "%"
        else:
            words = re.findall(r"[a-z]+", m[mt.end():mt.end() + 40])[:3]
            words = [w for w in words if w not in ("de", "of", "the", "los", "las", "los")]
            unit = ""
            if any(UNIT_MAP.get(w) == "RECORDS" for w in words):
                unit = "RECORDS"
            elif words:
                unit = NORM.normalize_unit(words[0])
        out.append((num, unit, words[0] if not mt.group(2) and words else ""))
    return out


def _scan(pattern_list, s):
    hits = []
    for act, rx in pattern_list:
        for m in re.finditer(rx, s):
            hits.append((m.start(), act, m))
    return sorted(hits, key=lambda x: x[0])


def _range_to_period(dates):
    """('2025-01-01','2025-03-31') -> 'Q1-2025' ; month / year ranges likewise; anything else stays as-is."""
    import calendar
    if len(dates) != 2:
        return None
    (y1, m1, d1), (y2, m2, d2) = [tuple(int(x) for x in d.split("-")) for d in sorted(dates)]
    if y1 == y2 and d1 == 1 and d2 == calendar.monthrange(y2, m2)[1]:
        if m1 == m2:
            return f"{y1}-{m1:02d}"
        if (m1, m2) in ((1, 3), (4, 6), (7, 9), (10, 12)):
            return f"Q{(m1 - 1) // 3 + 1}-{y1}"
        if (m1, m2) == (1, 12):
            return str(y1)
    return None


_resolve_relative_time = resolve_relative_time_str  # translator-layer alias (see aixl.core.ontology)


AGE_UNIT = {"ano": "YEAR", "anos": "YEAR", "year": "YEAR", "years": "YEAR",
            "mes": "MONTH", "meses": "MONTH", "month": "MONTH", "months": "MONTH",
            "dia": "DAY", "dias": "DAY", "day": "DAY", "days": "DAY"}
AGE_RX = [
    (">", re.compile(r"\bolder than\s+(\d+|one)\s+(anos?|years?|meses?|months?|dias?|days?)\b", re.I)),
    (">", re.compile(r"\bmas de\s+(\d+|un|una)\s+(anos?|meses?|dias?)\s+de\s+antiguedad\b", re.I)),
    ("<", re.compile(r"\bnewer than\s+(\d+|one)\s+(anos?|years?|meses?|months?|dias?|days?)\b", re.I)),
    ("<", re.compile(r"\bmenos de\s+(\d+|un|una)\s+(anos?|meses?|dias?)\s+de\s+antiguedad\b", re.I)),
]

CLOCK_TIME = re.compile(
    r"\b(?P<dir>antes de|before|prior to|by|no later than|despues de|after|later than)\s+(?:las?\s+)?"
    r"(?P<h>\d{1,2})(?:[:h](?P<m>\d{2}))?\s*(?P<ap>a\.?m\.?|p\.?m\.?)?\b", re.I)
BEFORE_WORDS = {"antes de", "before", "prior to", "by", "no later than"}
AT_TIME = re.compile(
    r"\b(?:at|for|para|a las)\s+(?:las?\s+)?"
    r"(?P<h>\d{1,2})(?:[:h](?P<m>\d{2}))?\s*(?P<ap>a\.?m\.?|p\.?m\.?)?\b", re.I)

SLASH_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/((?:19|20)\d\d)\b")


def _extra_time_extensions(frame, text_stripped: str) -> None:
    """0.3 extensions found missing by set 6 (E-DATE, 2026-09-27): slash dates (DD/MM/YYYY, the 0.2
    analyzer only understands ISO / 'day de month de year'), a two-day range sharing one month+year
    ('entre el 1 y el 15 de agosto de 2026' — the 0.2 analyzer only kept the second day), a clock-time
    BEFORE=/AFTER= constraint (12h or 24h, so '3:00 pm' and '15:00' compare equal instead of the time
    of day being silently dropped — that used to be a false EQUIVALENT for two genuinely different
    deadlines), and an AGE/duration constraint ('older than one year' / 'más de un año de antigüedad')."""
    s = text_stripped
    existing = set(frame.time.split(",")) if frame.time else set()
    added = []
    for m in SLASH_DATE.finditer(s):
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        iso = f"{y}-{mo:02d}-{d:02d}"
        if iso not in existing:
            existing.add(iso); added.append(iso)
    mon = "|".join(sorted(legacy.MONTHS, key=len, reverse=True))
    for m in re.finditer(rf"\b(\d{{1,2}})\s+(?:y|al|a|and|to)\s+(?:el\s+)?(\d{{1,2}})\s+(?:de\s+)?(?:{mon})\s*(?:de\s+)?((?:19|20)\d\d)\b", s):
        mname = next(n for n in legacy.MONTHS if re.search(rf"\b{n}\b", m.group(0)))
        num, _code = legacy.MONTHS[mname]
        y = m.group(3)
        for d in (int(m.group(1)), int(m.group(2))):
            iso = f"{y}-{num:02d}-{d:02d}"
            if iso not in existing:
                existing.add(iso); added.append(iso)
    if added:
        frame.time = ",".join(sorted(existing))

    def _24h(mo):
        h = int(mo.group("h")); mm = mo.group("m") or "00"; ap = mo.group("ap")
        if ap:
            ap = ap[0].lower()
            if ap == "p" and h != 12: h += 12
            if ap == "a" and h == 12: h = 0
        return f"{h:02d}:{mm}"

    for mo in CLOCK_TIME.finditer(s):
        if not (mo.group("m") or mo.group("ap")):
            continue                                      # bare number after "before/after": not a clock time
        code = "BEFORE" if mo.group("dir").lower() in BEFORE_WORDS else "AFTER"
        frame.constraints.append(f"{code}={_24h(mo)}")
    for mo in AT_TIME.finditer(s):
        if not (mo.group("m") or mo.group("ap")):
            continue                                      # bare number after "at/for/para": not a clock time
        frame.constraints.append(f"TIME_AT={_24h(mo)}")

    for op, rx in AGE_RX:
        m = rx.search(s)
        if m:
            n = 1 if m.group(1).lower() in ("one", "un", "una") else int(m.group(1))
            unit = AGE_UNIT[m.group(2).lower()]
            frame.constraints.append(f"AGE{op}{n}:{unit}")
            break


def _prepare_frame(text: str, today: date | None):
    """Preprocessing stage: text normalization, structured conditions/assertions/passives extraction
    (with clause masking), the 0.2 analyzer pass, and time resolution. Returns everything the
    action-detection stage in to_graph() needs, in the same order it was computed before extraction."""
    pre = _preprocess(text)
    pre = _fold_inflections(pre)
    pre, conds = _cond_clauses(pre)
    a_conds, a_spans = _assertions(pre)
    if a_spans:
        s0 = strip_accents(pre)
        pre = _mask(pre, [sp for sp in a_spans]) if len(s0) == len(pre) else pre
    conds += a_conds
    passives, p_spans = _passive(pre)
    if p_spans:
        pre = _mask(pre, p_spans) if len(strip_accents(pre)) == len(pre) else pre
    frame, warns = legacy.analyze(pre)
    frame.raw = text
    conf: dict = {}

    s = strip_accents(pre)
    frame.time = _resolve_relative_time(frame.time, today or date.today())
    _extra_time_extensions(frame, s)
    return frame, pre, s, conds, passives, warns, conf


def _apply_forbidden_allowed(frame, forbidden: set, allowed: set) -> None:
    for a in sorted(forbidden):
        if a in frame.actions:
            if "NO_" + a not in frame.negations:
                frame.negations.append("NO_" + a)
            if "FORBID_" + a not in frame.constraints:
                frame.constraints.append("FORBID_" + a)
    for a in sorted(allowed - forbidden):
        frame.constraints.append("ALLOW_" + a)
        frame.conditions = [c for c in frame.conditions if c != "AMBIGUOUS_MODALITY"]


def _apply_step_order(frame, s: str) -> bool:
    """'X antes de Y' / 'X after Y-ing' reorder the actions; returns whether order was stated at all."""
    ordered = bool(re.search(r"\b(luego|despues|then|afterwards|primero|first|depois|antes de|before|after)\b", s))
    for m in re.finditer(r"\b(antes de|before|despues de|after|depois de)\s+([a-z]+)", s):
        act = _action_of_word(m.group(2))
        if act and act in frame.actions:
            rest = [a for a in frame.actions if a != act]
            frame.actions = (rest + [act]) if m.group(1) in ("antes de", "before") else ([act] + rest)
    return ordered


def _apply_quantities_and_selection(frame, pre: str, s: str, conf: dict) -> None:
    """Quantities (0.2 COUNT replaced), ranking cues -> LIMIT, selection FIRST/LAST."""
    frame.constraints = [c for c in frame.constraints if not c.startswith("COUNT=")]
    qs = _quantities(pre, frame)
    ranking = bool(RANK_CUE.search(s))
    for num, unit, w1 in qs:
        if w1 in ("mejores", "best", "principales", "principais", "top", "main", "leading") or (ranking and len(qs) == 1 and not any(c.startswith("LIMIT=") for c in frame.constraints)):
            frame.constraints.append(f"LIMIT={num}")
            continue
        frame.constraints.append(f"QTY={num}" + (f":{unit}" if unit else ""))
        conf[frame.constraints[-1]] = 0.95
    for m in SELECT_RX.finditer(s):
        nxt = re.match(r"\s*(?:de\s+)?([a-z]+)", s[m.end():])
        if nxt and nxt.group(1) in TIME_UNITS:
            continue
        frame.constraints.append("SELECT=" + ("FIRST" if m.group(1).startswith(("primer", "first")) else "LAST"))


def _apply_aggregate_qualifiers(frame, s: str) -> None:
    for rx, code in AGG_MAP:
        for m in re.finditer(rf"\b{rx}\s+(?:las?\s+|los\s+|the\s+)?(\w+)", s):
            word = m.group(1)
            for dcode, drx in legacy.DATA_RX:
                if re.fullmatch(drx.replace(r"\b", ""), word) and dcode in frame.data:
                    frame.data[frame.data.index(dcode)] = f"{code}_{dcode}"
                    break


def _detect_output_format(frame, s: str) -> None:
    """Output formats beyond the 0.2 list."""
    if not frame.output:
        m = re.search(r"\b(?:en|como|as|in|into|to|a|para|em)\s+(?:un\s+|una\s+|uma\s+|a\s+)?(?:formato\s+(?:de\s+)?|format\s+|archivo\s+)?(pdf|xlsx|excel|html|xml|docx|word)\b", s)
        if m:
            frame.output = [OUTPUT_ALIASES[m.group(1)]]
        else:
            m = re.search(r"\b(json|csv|table|tabla|tabela|markdown|pdf)\s+(?:summary|report|resumen|reporte|file|archivo)\b", s)
            if m:
                frame.output = [{"tabla": "TABLE", "tabela": "TABLE", "table": "TABLE"}.get(m.group(1), m.group(1).upper())]
    if not frame.output:
        m = re.search(r"\b(?:formato\s+de\s+|em\s+forma\s+de\s+|en\s+forma\s+de\s+)(tabla|tabela|json|csv)\b", s)
        if m:
            frame.output = [{"tabla": "TABLE", "tabela": "TABLE"}.get(m.group(1), m.group(1).upper())]


def _apply_without_constraint(frame, s: str) -> None:
    """'without X' (noun, not a verb) is an explicit exclusion constraint."""
    for m in re.finditer(r"\b(?:sin|without|sem)\s+(?:(?:un|una|uma|a|an|el|la|los|las|the|o|os|as)\s+)?([a-z]{3,})\b", s):
        if not _action_of_word(m.group(1)) and not _action_of_word(re.sub(r"(ando|iendo|ing)$", "", m.group(1))):
            frame.constraints.append("WITHOUT=" + m.group(1).upper())


def _apply_visibility(frame, s: str) -> None:
    if re.search(r"\b(publico|publica|publicos|publicas|public|publicly)\b", s):
        frame.constraints.append("VISIBILITY=PUBLIC")
    if re.search(r"\b(privado|privada|privados|privadas|private|confidencial|restringido|restringida)\b", s):
        frame.constraints.append("VISIBILITY=PRIVATE")


def _apply_date_relation_constraints(frame, s: str) -> None:
    """before / after a date or period already extracted."""
    for t in (frame.time.split(",") if frame.time else []):
        for kw, con in ((r"antes de(?:l| la| el)?|before|prior to", "BEFORE"), (r"despues de(?:l| la| el)?|after|later than", "AFTER")):
            if re.search(rf"\b(?:{kw})\s+(?:el\s+)?{re.escape(t.lower())}", s):
                frame.constraints.append(f"{con}={t}")


def _collapse_date_range_to_period(frame) -> None:
    """date ranges equal to a quarter/month/year."""
    isos = [t for t in frame.time.split(",") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t)] if frame.time else []
    per = _range_to_period(isos)
    if per:
        frame.time = ",".join([t for t in frame.time.split(",") if t not in isos] + [per])


def _apply_name_references(frame, text: str) -> None:
    """names (recipients, quoted names) as references."""
    for n in _names(text, frame):
        if n not in frame.references:
            frame.references.append(n)


def _apply_numeric_references(frame, s: str) -> None:
    """0.3 extension (E-DATE round 3, 2026-09-27): 'ticket/issue/event/report N' or 'N° 77' / 'number
    77' without a literal '#' is still a reference, not a quantity (found by set 8 S8-008/030/061/095)."""
    for m in re.finditer(
        r"\b(?:ticket|issue|caso|case|reporte|report|evento|event|documento|document|informe|solicitud|request)\s+"
        r"(?:numero|n[uú]mero|number|no\.?|num\.?)?\s*#?(\d+)\b|"
        r"\b(?:numero|n[uú]mero|number|no\.?|num\.?)\s+#?(\d+)\b", s):
        ref = "#" + (m.group(1) or m.group(2))
        if ref not in frame.references:
            frame.references.append(ref)


def _filter_structured_conditions(frame, conds: list) -> None:
    """structured conditions replace literal fragments the 0.2 analyzer could not normalize."""
    if conds:
        struct = re.compile(r"^(?:[A-Z_]+_EXISTS|COUNT[<>=]+[\w.:]+|H[<>=!]+[\w.]+|(?:NOT_)?CONTAINS:\w+)$")
        frame.conditions = [c for c in frame.conditions if struct.match(c) or c in ("AMBIGUOUS_YEAR", "AMBIGUOUS_MODALITY")]


def _derive_intent_goal(frame, conf: dict) -> None:
    neg = [n[3:] for n in frame.negations]
    frame.intent = derive_intent(frame.actions, neg)
    frame.goal = derive_goal(frame.actions, frame.entities, neg)
    for c in frame.conditions:
        if c.startswith('"') or (" " in c and not c.startswith(("COUNT", "H"))):
            conf[c] = 0.6


def to_graph(text: str, today: date | None = None) -> SemanticGraph:
    frame, pre, s, conds, passives, warns, conf = _prepare_frame(text, today)
    pos: dict = {}
    for act, rx in legacy.ACTION_RX:
        for m in re.finditer(rx, s):
            pos.setdefault(act, m.start())
    extra = [e for e in _scan(EXTRA_ACTION_RX, s) if not re.search(r"\b(?:the|a|an|el|la|un|una|o|os|uma|este|esta|that|this)\s+$", s[max(0, e[0] - 8):e[0]])]
    for start, act, _m in extra:
        pos.setdefault(act, start)
    for start, act, _neg in passives:
        pos.setdefault(act, start)
    forbidden, allowed = set(), set()
    for act, start in pos.items():
        before = s[max(0, start - 40):start]
        if re.search(r"(?:not|never|don't|no|nunca)\s+(?:allow|permit)\w*\s+(?:\w+\s+){0,3}$", before) or FORBID_CUE.search(before) \
                or re.search(r"\b(?:sin|without|sem)\s+$", before):
            forbidden.add(act)
        elif ALLOW_CUE.search(before):
            allowed.add(act)
        elif legacy.NEG_BEFORE.search(before) and act in [e[1] for e in extra]:
            forbidden.add(act)
    for act, start in pos.items():
        if re.match(r".{0,50}?\b(?:is|are|es|son|e|sao|sera|seran)\s+(?:strictly\s+|totalmente\s+)?(?:forbidden|prohibited|prohibido|prohibida|prohibidos|proibido|proibida|not allowed|no permitido)", s[start:start + 90]):
            forbidden.add(act)
    for _st, act, neg in passives:
        if neg:
            forbidden.add(act)
    # deontic cue with no recognised action ("permite que vean...", "prohíbe que ..."): keep the modality on UNSPECIFIED
    FORB = re.compile(r"\b(?:prohib\w*|proib\w*|forbid\w*|impide\w*|impedir|impid\w*|vet(?:a|ar|es|o)|deny|denies|denegar|disallow\w*|no\s+permit\w*|not\s+allow\w*|no\s+autoriz\w*)\b")
    ALLW = re.compile(r"\b(?:permit\w*|allow\w*|autoriz\w*|authori[sz]\w*|deja\s+que|let)\b")
    deontic = None
    cue = FORB.search(s)
    if cue and not any(-70 < start - cue.start() < 70 and a in forbidden for a, start in pos.items()):
        deontic = "FORBID"
    else:
        cue = ALLW.search(s)
        if cue and not FORB.search(s) and not any(-70 < start - cue.start() < 70 and a in allowed for a, start in pos.items()):
            deontic = "ALLOW"
    all_acts = set(frame.actions) | {e[1] for e in extra} | {p[1] for p in passives}
    if deontic:
        all_acts.add("UNSPECIFIED"); pos["UNSPECIFIED"] = cue.start()
        (forbidden if deontic == "FORBID" else allowed).add("UNSPECIFIED")
    if frame.lang == "pt" and "EXCLUDE" in all_acts and not re.search(r"\bd[oa]s?\s+(?:relatorio|analise|resultado|conjunto|informe|report)", s):
        all_acts.discard("EXCLUDE"); all_acts.add("DELETE")          # PT "excluir X" (not "excluir X do relatório") = delete
        pos["DELETE"] = pos.get("EXCLUDE", 0)
        if "EXCLUDE" in forbidden:
            forbidden.discard("EXCLUDE"); forbidden.add("DELETE")
    frame.actions = sorted(all_acts, key=lambda a: pos.get(a, 10 ** 6))
    # --- tie-break (E-INTEROP, 2026-09-29): "generate/create/write A SUMMARY" is SUMMARIZE, not GENERATE —
    # the object names a more specific action already in the vocabulary, so that one wins. Found because two
    # independent LLM encoders of the same text split exactly on this (one read the verb literally, the other
    # read the object); this card/code rule makes both converge on the same choice instead of guessing.
    # ("resumen" as a NOUN also gets folded to "resume" by _fold_inflections upstream [it is also a valid verb
    # form, "ellos resumen"], which independently triggers SUMMARIZE alongside GENERATE -- both branches below
    # collapse to the same single SUMMARIZE action either way.) ---
    if ("GENERATE" in frame.actions or "CREATE" in frame.actions) and re.search(r"\bresum\w*\b|\bsummary\b", s):
        gen_act = "GENERATE" if "GENERATE" in frame.actions else "CREATE"
        if "SUMMARIZE" in frame.actions:
            frame.actions = [a for a in frame.actions if a != gen_act]
        else:
            frame.actions[frame.actions.index(gen_act)] = "SUMMARIZE"
            pos["SUMMARIZE"] = pos.get(gen_act, 0)

    _apply_forbidden_allowed(frame, forbidden, allowed)
    ordered = _apply_step_order(frame, s)
    _apply_quantities_and_selection(frame, pre, s, conf)
    frame.conditions += conds
    _apply_aggregate_qualifiers(frame, s)
    _detect_output_format(frame, s)
    _apply_without_constraint(frame, s)
    _apply_visibility(frame, s)
    _apply_date_relation_constraints(frame, s)
    _collapse_date_range_to_period(frame)
    _apply_name_references(frame, text)
    _apply_numeric_references(frame, s)
    _filter_structured_conditions(frame, conds)
    _derive_intent_goal(frame, conf)
    frame = _norm_frame(frame)
    frame.raw = text
    g = SemanticGraph.from_frame(frame, conf)
    g.meta["warnings"] = warns
    g.meta["ordered"] = ordered
    g.meta["text_stripped"] = strip_accents(text)
    return g


def to_frame(text: str, today: date | None = None) -> SemanticFrame:
    return to_graph(text, today).to_frame()
