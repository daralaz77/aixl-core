"""Out-of-lexicon object nouns (master prompt §66 transparency: LOSS must be reported, never silent).

The translator is closed-lexicon by design (no fuzzy matching). A noun it does not know ("factura", "invoice")
is dropped from the graph without trace, so "Generate the invoice" == "Generate" for the comparator. This module
finds those nouns so callers can WARN. It is deliberately narrow to stay quiet: it only looks at the word right
after a definite/indefinite article and flags it when no lexicon (nouns, units, time, months, languages, places,
number words, formats, verbs) accounts for it. It never changes the graph or the meaning; it only reports."""
import re

from aixl.core.normalizer import ALL_ACTION_RX, OUTPUT_ALIASES, STOP, UNIT_MAP, strip_accents
from aixl.legacy02.translators import natural_to_semantic as legacy

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


# --- ADR-016 step 1: what does NOT count as "unaccounted content" -------------------------------------------------
# (a) closed-class FUNCTION words: the graph represents their effect structurally (negation, comparator, ordering,
#     quantity scope, modality, condition); their loss is the comparator's job, not an open-slot problem.
FUNCTION_WORDS = set("""
 than must not more less most least top best worst first last all any every each some none only just also even still yet
 into onto over under above below between among within without with from for before after during until since while when
 if unless whether that this those these there here which whose who whom what where how why then than too very much many
 never always should shall will would could can may might need needs needed have has had been being are was were does did
 look turn make get put set take give one two three another other same both either neither once twice again already
 por para con sin sobre bajo entre desde hasta durante antes despues luego cuando mientras como donde cual cuales cuya
 cuyo cuyas cuyos que quien quienes debe deben deberia hay haber ser sea sean existan existe esta este estos estas esa
 ese eso esos esas aquel todo todos toda todas cada solo solamente tambien aun todavia nunca siempre mas menos mayor
 menor mejor mejores peor primero primera ultimo ultima principales otro otra otros otras mismo misma ambos ambas tras
 segun sino pero sobre ante contra mediante vez veces favor
 para pelo pela pelos pelas com sem sobre entre desde ate durante antes depois quando enquanto como onde qual quais cujo
 cuja cujos cujas quem deve devem deveria ha haver ser seja sejam existam existe esta este estes estas esse essa isso
 aquele todo todos toda todas cada somente tambem ainda nunca sempre mais menos maior menor melhor melhores pior primeiro
 primeira ultimo ultima principais outro outra outros outras mesmo mesma ambos ambas apos segundo porem contra mediante
 vez vezes favor
 prohibido proibido prohibida forbidden prohibited required requerido requerida requires require maximum maximo max minimum
 minimo min latest recent recientes recente recentes format formato table tabla tabela per task tarea tarefa number numero
 numeros nao no
""".split())

# (b) cross-lingual concept classes for GENERIC nouns/adjectives (closed, small, general vocabulary): two words of the
#     same class count as the SAME content, so a faithful translation is not reported as a difference.
_CONCEPT_ROWS = [
    "format formato formatos formats", "invoice factura fatura facturas faturas invoices", "number numero numeros numbers",
    "set conjunto conjuntos sets", "file files archivo archivos arquivo arquivos ficheiro", "table tabla tabelas tabela tables tablas",
    "language idioma idiomas language lingua linguas", "priority prioridad prioridade", "duplicates duplicados duplicate duplicado duplicadas",
    "average promedio media mean", "figures cifras cifra numeros valores figure", "name nombre nome", "price precio preco prices precios",
    "email correo mail courriel", "customer cliente clientes customers", "report reporte informe relatorio",
    "list lista listado listas", "result resultado resultados results", "record registro registros registo records",
    "value valor valores values", "date fecha data fechas", "total totales totals", "item items elemento elementos elemento itens",
]
_CONCEPT = {w: row.split()[0] for row in _CONCEPT_ROWS for w in row.split()}

_TOKEN = re.compile(r"\d+(?:[.,]\d+)?|[a-z]+")
_CLITIC = re.compile(r"(?<=[a-z]{4})(?:los|las|selo|selos|se|lo|la|le|les|me|nos)$")
_SUFFIX = re.compile(r"(?<=[a-z]{4})(?:ing|ed|ando|iendo|ado|ido|ada|ida|ados|idos|cion|ciones|coes|cao|ly|ment|mente)$")
_PLURAL = re.compile(r"(?<=[a-z]{3})(?:es|s)$")


def _forms(w: str) -> set[str]:
    """Surface variants of a word used only to decide 'is this accounted for' (never to compare meaning)."""
    if w[0].isdigit():
        try:
            f = float(w.replace(",", "."))
        except ValueError:
            return {w}
        out = {("%g" % f), ("%g" % (f * 100)), ("%g" % (f / 100)), ("%.2f" % f).rstrip("0").rstrip("."), ("%g" % f).lstrip("0")}
        return {x for x in out | {x.lstrip("0") for x in out} if x}
    out = {w}
    for _ in range(2):
        for x in list(out):
            out.add(_CLITIC.sub("", x)); out.add(_PLURAL.sub("", x))
    return {x for x in out if x}


def unaccounted_content(text: str, graph) -> list[str]:
    """ADR-016 step 1. Content words/numbers of the source text that neither a lexicon nor the graph's canonical form
    accounts for (anything the closed vocabulary silently dropped: 'weekly', 'CFO', 'AES', '15' ...). Unlike
    unrecognized_terms it is not limited to article+noun and it never changes the graph; it only supports the
    INCONCLUSIVE verdict (compare only looks at the DIFFERENCE between the two sides' lists)."""
    canon = repr(graph.canonical()).lower()
    out = []
    for w in _TOKEN.findall(strip_accents(text).lower()):
        if (len(w) < 3 and not w[0].isdigit()) or w in FUNCTION_WORDS:
            continue
        fs = _forms(w)
        if any((f in canon) if f[0].isdigit() else (_known(f) or f in canon) for f in fs):
            continue
        w = _CONCEPT.get(w, _CONCEPT.get(next(iter(sorted(fs - {w})), w), w))
        if w not in out:
            out.append(w)
    return sorted(out)


def stem(w: str) -> str:
    """Light, language-agnostic stem used ONLY to compare two sides' unaccounted words (publishing~published)."""
    if w[0].isdigit():
        return w
    for _ in range(2):
        w = _SUFFIX.sub("", _PLURAL.sub("", _CLITIC.sub("", w)))
    return w


_SHORT_FUNCTION = set("a o e y u de en el la lo le les se me te un ya al do da ni si to of in on at as by an is it or if be we he us up so my go".split())


def residue_key(clauses: list) -> tuple:
    """Canonical form of the R: residue (ADR-016): the sorted, de-duplicated, light-stemmed content words of all residue
    clauses (function words dropped, generic cross-lingual concepts collapsed). Order-free, so 'by WhatsApp' ~ 'WhatsApp'."""
    out = set()
    for c in clauses:
        for w in _TOKEN.findall(strip_accents(str(c)).lower()):
            if w in FUNCTION_WORDS or w in STOP or w in _SHORT_FUNCTION:
                continue
            out.add(stem(_CONCEPT.get(w, w)))
    return tuple(sorted(out))
