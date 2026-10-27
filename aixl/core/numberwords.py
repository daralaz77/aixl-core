"""Number words (ES / EN / PT) in one place, plus a small parser for compound numbers and a normaliser for clock times.

Found 2026-10-26: the translator's table stopped at a handful of words (`fourteen`, `catorce`, `quatorze`, `fifteen` ... were invisible), so `within fourteen days` and
`within fifteen days` compared EQUIVALENT in the core, and the critical-slot check compared `fourteen` with `14` as different numbers. `dos` is deliberately NOT here:
it is the number 2 in Spanish and `de + os` ("of the") in Portuguese (completeness refuses it, see aixl.core.completeness). `once` is not here either (English adverb)."""
import re

UNITS = {
    # English
    "zero": 0, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    # Spanish
    "cero": 0, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veintiuno": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
    # Portuguese
    "dois": 2, "duas": 2, "quatro": 4, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "treze": 13, "quatorze": 14, "quinze": 15, "dezesseis": 16,
    "dezasseis": 16, "dezessete": 17, "dezassete": 17, "dezoito": 18, "dezenove": 19,
}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
        "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
        "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60, "oitenta": 80}
HUNDREDS = {"hundred": 100, "cien": 100, "ciento": 100, "cem": 100, "cento": 100, "doscientos": 200, "trescientos": 300, "cuatrocientos": 400, "quinientos": 500,
            "seiscientos": 600, "setecientos": 700, "ochocientos": 800, "novecientos": 900, "duzentos": 200, "trezentos": 300, "quatrocentos": 400, "quinhentos": 500,
            "seiscentos": 600, "setecentos": 700, "oitocentos": 800, "novecentos_": 900}
THOUSAND = {"thousand": 1000, "mil": 1000}
# `one` / `uno` / `um` are also pronouns and articles: they count as 1 only before a unit of time or of count.
ONE = frozenset({"one", "uno", "un", "una", "um", "uma"})
_ONE_UNITS = frozenset("""day days hour hours week weeks month months year years minute minutes time times dia dias hora horas semana semanas mes meses ano anos
 minuto minutos vez vezes segundo segundos second seconds""".split())
WORDS = {**UNITS, **TENS, **HUNDREDS, **THOUSAND}
_VAL = {**UNITS, **TENS, **HUNDREDS}


def _deaccent(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def parse_words(tokens: list) -> list:
    """Numbers written in words in a list of lowercase, accent-stripped tokens: `twenty five` -> 25, `treinta y cinco` -> 35, `vinte e cinco` -> 25,
    `one hundred and five` -> 105, `dois mil` -> 2000, `quince` -> 15. `one`/`uno`/`um` only before a unit of time or count."""
    tokens = ["dois" if t == "dos" and k + 1 < len(tokens) and tokens[k + 1] == "mil" else t for k, t in enumerate(tokens)]     # `dos mil` = 2000
    out, i, n = [], 0, len(tokens)

    def is_num(t):
        return t in _VAL or t in THOUSAND

    while i < n:
        t = tokens[i]
        if t in ONE and i + 1 < n and tokens[i + 1] in _ONE_UNITS:
            out.append(1); i += 1; continue
        if not is_num(t):
            i += 1; continue
        total = cur = 0
        while i < n:
            t = tokens[i]
            if t in ("and", "y", "e") and i + 1 < n and cur and tokens[i + 1] in _VAL and _VAL[tokens[i + 1]] < 100 and (cur % 100 == 0 or 20 <= cur % 100 <= 90 and cur % 10 == 0):
                i += 1; continue
            if t in THOUSAND:
                total += (cur or 1) * 1000; cur = 0
            elif t in _VAL:
                v = _VAL[t]
                if v == 100 and t == "hundred" and cur:
                    cur *= 100
                elif v >= 100 and cur % 100 == 0 and cur and cur >= v:
                    break
                elif v < 100 and cur and (cur % 100) and (cur % 100) % 10 != 0 and v >= 1:
                    break                                      # `fifteen six`: two numbers, not one
                elif v < 10 and cur % 10:
                    break
                else:
                    cur += v
            else:
                break
            i += 1
        out.append(total + cur)
    return out


_CLOCK = [
    (re.compile(r"(?<![\d:.,])(\d{1,2}):(\d{2})\s*(a\.?m\.?|p\.?m\.?)?(?![\d:])"), lambda m: (m.group(1), m.group(2), m.group(3))),
    (re.compile(r"(?<![\d:.,])(\d{1,2})\s*(a\.?m\.?|p\.?m\.?)(?![a-z])"), lambda m: (m.group(1), "00", m.group(2))),
    (re.compile(r"(?<![\d:.,])(\d{1,2})\s*h(?:oras?)?\s*(\d{2})?(?![a-z\d])"), lambda m: (m.group(1), m.group(2) or "00", None)),
    (re.compile(r"(?<![\d:.,])(\d{1,2})\s+(?:de la|da|de)\s+(manana|tarde|noche|madrugada|manha)(?![a-z])"),
     lambda m: (m.group(1), "00", "pm" if m.group(2) in ("tarde", "noche") else "am")),
]
_NOON = re.compile(r"(?<![a-z])(?:noon|midday|mediodia|meio dia|meio-dia)(?![a-z])")


def _hhmm(h: str, m: str, ap) -> str:
    hh = int(h)
    if ap:
        a = ap[0]
        if a == "p" and hh != 12:
            hh += 12
        if a == "a" and hh == 12:
            hh = 0
    return f"T{hh:02d}:{m}"


def clock_times(text: str):
    """(text with every clock time removed, set of canonical `T18:00` tokens). `6 pm`, `18:00`, `18h`, `6 de la tarde` and `6:00 p.m.` give the same token."""
    s = _deaccent(text).lower()
    found = set()
    for rx, parts in _CLOCK:
        def sub(m, parts=parts):
            h, mi, ap = parts(m)
            if int(h) > 24 or int(mi) > 59:
                return m.group(0)
            found.add(_hhmm(h, mi, ap)); return " "
        s = rx.sub(sub, s)
    if _NOON.search(s):
        found.add("T12:00"); s = _NOON.sub(" ", s)
    return s, found


_GROUPED = re.compile(r"(?<![\d.,])\d{1,3}(?:[.,]\d{3})+(?![\d])")
_PLAIN = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?(?![\w])")


def canonical_numbers(text: str) -> set:
    """Every number in the text as a canonical string: digits (`1.250.000` = `1,250,000` = `1250000`), words (`catorce` = 14) and clock times (`T18:00`)."""
    s, clocks = clock_times(text)
    out = set(clocks)

    def grouped(m):
        out.add(re.sub(r"[.,]", "", m.group(0))); return " "
    s = _GROUPED.sub(grouped, s)
    for m in _PLAIN.finditer(s):
        v = m.group(0).replace(",", ".")
        out.add(v.rstrip("0").rstrip(".") if "." in v else v)
    toks = re.findall(r"[a-z]+", re.sub(r"(?<=[a-z])-(?=[a-z])", " ", s))
    out.update(str(v) for v in parse_words(toks))
    return out
