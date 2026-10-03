"""FASE 4 — SemanticNormalizer: controlled equivalences (synonyms, dates, numbers, units, formats).

Design rule (spec §11): similarity of wording is never enough. This module only maps expressions that are
declared equivalent in a closed lexicon; it does not compute fuzzy similarity. Context-dependent phrases
("total de ventas" vs "ventas") are kept DIFFERENT through an explicit `aggregate` attribute.
"""
import re
import unicodedata

from aixl.legacy02.translators import natural_to_semantic as legacy


_INVISIBLE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff\u00ad]")
# Cyrillic/Greek letters that render like Latin ones. Only folded INSIDE a word that also has Latin letters
# (a mixed-script word is the homoglyph-attack signature; ES/EN/PT text never has one legitimately).
_CONFUSABLE = {"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ѕ": "s", "ј": "j", "ԁ": "d", "ɡ": "g",
               "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X",
               "ο": "o", "Ο": "O", "ν": "v", "ι": "i", "α": "a", "ρ": "p"}


def sanitize_input(text: str) -> tuple[str, list]:
    """Defence against invisible-character / lookalike-letter obfuscation (§39). Returns (clean_text, findings);
    findings is empty for ordinary text, so callers can surface a warning without changing anything else."""
    findings = []
    if _INVISIBLE.search(text):
        findings.append("INVISIBLE_CHARACTERS")
        text = _INVISIBLE.sub("", text)
    folded = unicodedata.normalize("NFKC", text)             # fullwidth / compatibility forms -> plain ASCII
    if folded != text:
        findings.append("COMPATIBILITY_FORMS")
        text = folded

    def fix(m):
        w = m.group(0)
        if re.search(r"[A-Za-z]", w) and any(c in _CONFUSABLE for c in w):
            findings.append("MIXED_SCRIPT_HOMOGLYPHS")
            return "".join(_CONFUSABLE.get(c, c) for c in w)
        return w
    text = re.sub(r"[^\W\d_]+", fix, text)
    return text, findings


def strip_accents(s: str) -> str:
    return "".join(unicodedata.normalize("NFD", c)[0] for c in s).lower()


# ---- extension actions (verbs the 0.2 lexicon does not cover), matched on accent-stripped lowercase text ----
EXTRA_ACTION_RX = [
    ("ENABLE",  r"\b(activ(a|ar|e|es)|ativ(a|ar|e|es)|habilit(a|ar|e|es)|enable[sd]?|enciende|encender|turn on)\b"),
    ("DISABLE", r"\b(desactiv(a|ar|e|es)|desativ(a|ar|e|es)|deshabilit(a|ar|e|es)|disable[sd]?|apaga|apagar|apagues?|turn off|archiv(a|ar|e|es)|archive[sd]?|suspend(e|es|er)?)\b"),
    ("SEND",    r"\b(envi(a|ar|e|es|en)|mand(a|ar|es|e)|remit(e|es|ir|a)|send[s]?|sent|notific(a|ar|e|es|ame)|notify|notifies|e-?mail(s|ed|ing)?|avis(a|ar|e|es)|alert(s|ed)?)\b"),
    ("INCLUDE", r"\b(inclu(ye|yes|ir|ya|yas|a|i|am|em)|include[sd]?|incorpor(a|ar|e|es))\b"),
    ("EXCLUDE", r"\b(exclu(ye|yes|ir|ya|yas|i|is|a)|exclude[sd]?|omit(e|es|ir)|omit|descarta(r)?|descarte|discard[s]?)\b"),
    ("UPDATE",  r"\b(actuali[zc](a|ar|e|es|en)|update[sd]?|modific(a|ar|ue|ues)|modify|edit(a|ar|e|es)?|cierra(s)?|close[sd]?|resuelve(s)?|resolve[sd]?|marc(a|ar|as)|mark(s|ed)?|flag(s|ged|ging)?)\b"),
    ("CREATE",  r"\b(program(a|ar|as|e)|schedul(e|es|ed|ing)|agenda(r)?)\b"),
]

# Single source of truth for "every action verb the translator knows" (0.2 base + 0.3 extensions),
# so callers that need the full vocabulary reference this list instead of each re-concatenating
# `legacy.ACTION_RX + EXTRA_ACTION_RX` by hand (that pattern was duplicated across 5 call sites and
# is easy to get wrong by silently omitting `EXTRA_ACTION_RX`). Order preserved: legacy first, then
# extensions, exactly as every prior call site computed it.
ALL_ACTION_RX = legacy.ACTION_RX + EXTRA_ACTION_RX

FORBID_CUE = re.compile(r"(?:prohib\w*|proib\w*|forbid\w*|forbidden|not allowed|no (?:esta )?permitid\w*|no se permite|veto\w*)\s+(?:\w+\s+){0,2}$")
ALLOW_CUE = re.compile(r"(?:permit\w*|allow\w*|autoriz\w*|se permite|is allowed to|are allowed to)\s+(?:\w+\s+){0,2}$")

# ---- units (closed) ; anything else alphabetic becomes an uppercase unit word ----
UNIT_MAP = {
    "registros": "RECORDS", "registro": "RECORDS", "records": "RECORDS", "record": "RECORDS", "rows": "RECORDS", "row": "RECORDS",
    "filas": "RECORDS", "fila": "RECORDS", "entries": "RECORDS", "entradas": "RECORDS",
    "usuarios": "USERS", "users": "USERS", "usuario": "USERS", "user": "USERS",
    "clientes": "CUSTOMERS", "customers": "CUSTOMERS", "clients": "CUSTOMERS", "cliente": "CUSTOMERS",
    "ventas": "SALES", "sales": "SALES", "imagenes": "IMAGES", "images": "IMAGES", "audios": "AUDIOS", "videos": "VIDEOS",
    "reportes": "REPORTS", "informes": "REPORTS", "reports": "REPORTS", "documentos": "DOCUMENTS", "documents": "DOCUMENTS",
    "eventos": "EVENTS", "events": "EVENTS", "paginas": "PAGES", "pages": "PAGES", "archivos": "FILES", "files": "FILES",
    "productos": "PRODUCTS", "products": "PRODUCTS", "personas": "PEOPLE", "people": "PEOPLE", "anomalias": "ANOMALIES", "anomalies": "ANOMALIES", "anomalia": "ANOMALIES", "anomaly": "ANOMALIES",
    "empresas": "COMPANIES", "companies": "COMPANIES", "resultados": "RESULTS", "results": "RESULTS", "errores": "ERRORS", "errors": "ERRORS", "erros": "ERRORS",
}
STOP = set("de del en con para y o e the of in from and with to for al las los la el un una por que si if then a an on at is are es".split())

AGG_MAP = [
    (r"(?:volumen de|volume of|total de|total of|total|suma de|sum of)", "TOTAL"),
    (r"(?:promedio de|media de|average of|average|mean of|mean)", "AVERAGE"),
    (r"(?:numero de|number of|count of|cantidad de|cuantos|cuantas|how many|quantos|quantas)", "COUNT"),
]
OUTPUT_ALIASES = {"excel": "XLSX", "xlsx": "XLSX", "pdf": "PDF", "html": "HTML", "xml": "XML", "docx": "DOCX", "word": "DOCX"}


class SemanticNormalizer:
    """Facade over the closed lexicons; each method returns the canonical concept or None (never a guess)."""

    def normalize_number(self, s: str, lang: str = "es") -> str:
        s = s.strip()
        if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):            # 1.000 / 1,000 -> 1000 (thousands)
            return re.sub(r"[.,]", "", s)
        if re.fullmatch(r"\d+,\d+", s):                          # 0,75 -> 0.75
            return s.replace(",", ".")
        return s

    def normalize_unit(self, word: str) -> str:
        w = strip_accents(word)
        if w in UNIT_MAP:
            return UNIT_MAP[w]
        return w.upper() if w.isalpha() and len(w) >= 3 and w not in STOP else ""

    def normalize_time(self, text: str) -> str | None:
        f, _ = legacy.analyze("analiza " + text)
        return f.time or None

    def normalize_action(self, word: str) -> str | None:
        s = strip_accents(word)
        for act, rx in ALL_ACTION_RX:
            if re.search(rx, s):
                return act
        return None

    def normalize_output(self, word: str) -> str | None:
        w = strip_accents(word)
        return OUTPUT_ALIASES.get(w) or (w.upper() if w.upper() in ("JSON", "CSV", "MARKDOWN", "AIXL", "TABLE", "TEXT") else None)

    def normalize_aggregate(self, qualifier: str) -> str | None:
        q = strip_accents(qualifier).strip()
        for rx, code in AGG_MAP:
            if re.fullmatch(rx, q):
                return code
        return None

    def canonical_equal(self, a: str, b: str) -> bool:
        """True only if both expressions normalize to the same time/action/output; never by string similarity."""
        for fn in (self.normalize_time, self.normalize_action, self.normalize_output):
            x, y = fn(a), fn(b)
            if x and y and x == y:
                return True
        return False
