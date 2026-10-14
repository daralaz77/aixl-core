"""Deliberately NOT here (already modelled elsewhere; a second path double-counts or breaks convergence): older/newer than (AGE), recent (ORDER),
public/private (VISIBILITY), urgent/critical (priority), open/closed (ACTION CLOSE/OPEN).
Closed set of contrast modifiers (ES/EN/PT) whose swap changes meaning but which the core has no slot for: `old` -> `new`, `temporary` ->
`permanent`, `open` -> `closed`. Each concept is a canonical code; the translator emits `MOD=<codes>` so every comparator sees a change, and
completeness treats the words as accounted ONLY when the graph carries their code. Chosen by arena lex_swap findings + frequency of unaccounted
adjectives (2026-10-13); small on purpose — a word outside the table stays unaccounted (the published layers abstain), never silently equal."""
import re

from aixl.core.normalizer import strip_accents

_RAW = {
    "OLD": "old|antiguo|antiguos|antigua|antiguas|viejo|viejos|vieja|viejas|antigo|antigos|antiga|antigas|velho|velhos|velha|velhas",
    "NEW": "new|nuevo|nuevos|nueva|nuevas|novo|novos|nova|novas",
    "TEMP": "temporary|temp|temporal|temporales|temporario|temporarios|temporaria|temporarias|provisional|provisorio",
    "PERM": "permanent|permanente|permanentes",
    "DUP": "duplicate|duplicates|duplicated|repeated|redundant|redundante|redundantes|duplicado|duplicados|duplicada|duplicadas|duplicata|duplicatas|repetido|repetidos|repetida|repetidas",
    "UNIQ": "unique|unico|unicos|unica|unicas",
    "ACTIVE": "active|activo|activos|activa|activas|ativo|ativos|ativa|ativas",
    "INACTIVE": "inactive|inactivo|inactivos|inactiva|inactivas|inativo|inativos|inativa|inativas|dormant",
    "PAID": "paid|pagado|pagados|pagada|pagadas|pago|pagos|pagas",
    "UNPAID": "unpaid|impago|impagos|impaga|impagas|inadimplente|inadimplentes|moroso|morosos|morosa|morosas",
    "OVERDUE": "overdue|vencido|vencidos|vencida|vencidas|atrasado|atrasados|atrasada|atrasadas|late",
    "PENDING": "pending|pendiente|pendientes|pendente|pendentes",
    "APPROVED": "approved|aprobado|aprobados|aprobada|aprobadas|aprovado|aprovados|aprovada|aprovadas",
    "REJECTED": "rejected|rechazado|rechazados|rechazada|rechazadas|rejeitado|rejeitados|rejeitada|rejeitadas|denied",
    "FAILED": "failed|failing|fallido|fallidos|fallida|fallidas|falhado|falhados|falhada|falhadas|fracassado",
    "SUCCESSFUL": "successful|exitoso|exitosos|exitosa|exitosas|bem-sucedido|sucedido",
    "PRIMARY": "primary|principal|principales|primario|primarios|primaria|primarias",
    "SECONDARY": "secondary|secundario|secundarios|secundaria|secundarias",
    "INTERNAL": "internal|interno|internos|interna|internas",
    "EXTERNAL": "external|externo|externos|externa|externas",
    "PROD": "production|produccion|producao",
    "STAGING": "staging|preproduccion|homologacao",
}
_COMPARATIVE = {"older": "OLD", "oldest": "OLD", "newer": "NEW", "newest": "NEW"}
_STRIP = lambda w: strip_accents(w).lower()      # noqa: E731
WORD_CODE = {w: code for code, ws in _RAW.items() for w in ws.split("|")}
_TOK = re.compile(r"(?<![a-z0-9])[a-z]+(?:-[a-z]+)?(?![a-z0-9])")


def codes_in(text: str) -> list:
    """Sorted unique canonical modifier codes mentioned in `text`."""
    toks = _TOK.findall(strip_accents(text).lower())
    out = {WORD_CODE[t] for t in toks if t in WORD_CODE}
    for i, t in enumerate(toks):         # `keep the older record` is a modifier; `older than 1 year` is the AGE constraint (modelled elsewhere)
        if t in _COMPARATIVE and not (i + 1 < len(toks) and toks[i + 1] in ("than", "que", "do")):
            out.add(_COMPARATIVE[t])
    return sorted(out)


def accounted_words(constraints) -> set:
    """Words of the table whose code is carried by a `MOD=` constraint (their meaning is in the graph)."""
    have = set()
    for c in constraints:
        if c.startswith("MOD="):
            have |= set(c[4:].split(","))
    return {w for w, code in WORD_CODE.items() if code in have}


# --- modality strength: `must` is the unmarked imperative (Delete == You must delete), so only the WEAKER readings are emitted -----------------
_MODAL_RAW = {
    "SHOULD": ["should", "ought to", "deberias", "deberia", "deberian", "convendria", "conviene", "deveria", "deverias", "recomendable", "recommended"],
    "MAY": ["may", "can", "might", "puedes", "puede", "pueden", "podes", "podras", "podra", "pode", "podem", "podes", "allowed to", "permitted to",
            "feel free to", "esta permitido", "es posible", "libre de", "tienes permiso", "tem permissao"],
}
_MONTH_CTX_PREV = {"in", "of", "during", "until", "before", "after", "from", "since", "by", "en", "de", "desde", "hasta", "em", "ate", "antes", "despues"}


def modal_codes(text: str) -> list:
    """`SHOULD` / `MAY` / `SHOULD_NOT` / `MAY_NOT` present in `text`. `must`/`debes`/`deve` and the bare imperative are the same (no code);
    `must not` is the prohibition the negation already carries (no code). `May` the month is excluded by its neighbours."""
    s = " " + " ".join(_TOK.findall(strip_accents(text).lower())) + " "
    polite = "?" in text or "\u00bf" in text      # `Can you send it?` / `¿Puedes enviarlo?` is a polite imperative, not a permission
    out = []
    for code, phrases in _MODAL_RAW.items():
        for p in phrases:
            for m in re.finditer(r"(?<= )" + re.escape(p) + r"(?= )", s):
                before = s[:m.start()].split()
                after = s[m.end():].split()
                if code == "MAY" and (polite or after[:1] == ["you"]) and p in ("can", "may", "puedes", "puede", "pode", "podes", "podem", "might"):
                    continue
                if p == "may" and ((before and before[-1] in _MONTH_CTX_PREV) or (after and after[0].isdigit())):
                    continue
                out.append(code + ("_NOT" if after[:1] in (["not"], ["never"]) or (code == "MAY" and p in ("can",) and after[:1] == ["not"]) else ""))
    if re.search(r"(?<![a-z])cannot(?![a-z])|(?<![a-z])can t(?![a-z])|(?<![a-z])cant(?![a-z])", s) or " no puedes " in s or " nao pode " in s:
        out.append("MAY_NOT")
    import collections
    return sorted(c if n == 1 else f"{c}:{n}" for c, n in collections.Counter(out).items())      # a SECOND `may` is a change too


def modal_words() -> set:
    return {w for ps in _MODAL_RAW.values() for p in ps for w in p.split()}
