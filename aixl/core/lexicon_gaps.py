"""Out-of-lexicon object nouns (master prompt §66 transparency: LOSS must be reported, never silent).

The translator is closed-lexicon by design (no fuzzy matching). A noun it does not know ("factura", "invoice")
is dropped from the graph without trace, so "Generate the invoice" == "Generate" for the comparator. This module
finds those nouns so callers can WARN. It is deliberately narrow to stay quiet: it only looks at the word right
after a definite/indefinite article and flags it when no lexicon (nouns, units, time, months, languages, places,
number words, formats, verbs) accounts for it. It never changes the graph or the meaning; it only reports."""
import re

from aixl.legacy02.translators import natural_to_semantic as legacy
from aixl.core.normalizer import ALL_ACTION_RX, strip_accents, UNIT_MAP, OUTPUT_ALIASES, STOP

ARTICLE_NOUN = re.compile(r"\b(?:el|la|los|las|un|una|unos|unas|o|os|a|as|um|uma|the|an)\s+([a-z]{4,})\b")
_ORD_AND_TIME = {"primer", "primero", "primera", "segundo", "tercer", "ultimo", "ultima", "proximo", "proxima", "pasado", "pasada",
                 "semana", "mes", "ano", "anos", "dia", "dias", "week", "month", "year", "day", "days", "hour", "hora", "trimestre",
                 "quarter", "semestre", "next", "last", "this", "same", "mismo", "misma", "other", "otro", "otra", "following", "previous",
                 # nominalised actions / handled concepts (recognised elsewhere in the pipeline)
                 "analisis", "analysis", "analise", "validacion", "validation", "validacao", "resumen", "summary", "traduccion", "translation",
                 "confianza", "confidence", "confianca", "total", "maximo", "minimo", "ultimos", "primeros", "otros", "outros", "high", "low", "urgent"}


def _known(w: str) -> bool:
    if w in STOP or w in UNIT_MAP or w in OUTPUT_ALIASES or w in _ORD_AND_TIME:
        return True
    from aixl.translators.natural_to_semantic import NONNAME, NUMBER_WORDS
    if w in NONNAME or w in NUMBER_WORDS or w in legacy.MONTHS or w in legacy.LANGS:
        return True
    for _a, rx in ALL_ACTION_RX:
        if re.fullmatch(rx.replace(r"\b", ""), w):
            return True
    for _c, rx in legacy.DATA_RX + legacy.ENTITY_RX + legacy.REL_RX:
        if re.search(rx, w):
            return True
    return False


def unrecognized_terms(text: str, graph=None) -> list[str]:
    """Article+noun words no lexicon accounts for. With `graph`, reports ONLY when the graph kept no ENTITY/DATA
    object at all (the silent-loss case: the sentence has an object noun but the meaning has none). Capitalised
    words (names) are never reported."""
    if graph is not None and (graph.by_type("ENTITY") or graph.by_type("DATA")):
        return []
    s = strip_accents(text)
    caps = {w.lower() for w in re.findall(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+", text)}
    out = []
    for m in ARTICLE_NOUN.finditer(s):
        w = m.group(1)
        if w not in caps and not _known(w) and w not in out:
            out.append(w)
    return out
