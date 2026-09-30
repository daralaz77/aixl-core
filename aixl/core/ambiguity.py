"""FASE 9 — AmbiguityDetector: says AMBIGUOUS instead of inventing an interpretation.

BLOCKING reasons make `ambiguous=True`; INFO notes (e.g. relative dates that need a clock) do not.
Each finding carries an extraction confidence (how sure the rule is), never a truth value."""
import re
from dataclasses import dataclass, field

from aixl.legacy02.translators import natural_to_semantic as legacy
from aixl.core.normalizer import strip_accents, EXTRA_ACTION_RX
from aixl.core.semantic_graph import SemanticGraph
from aixl.translators.natural_to_semantic import to_graph

PRONOUNS = (r"\b(eso|esto|aquello|ello|el otro|la otra|los otros|las otras|ambos|ambas|el mismo|la misma|"
            r"el|ella|ellos|ellas|it|them|they|he|she|him|her|that|this|those|these|the other one|the others?|both|"
            r"ele|ela|eles|elas|isso|aquilo)\b")
PRONOUN_STRICT = re.compile(r"\b(eso|esto|aquello|ello|el otro|la otra|los otros|las otras|ambos|ambas|"
                            r"ella|ellos|ellas|it|them|they|he|she|him|her|those|these|the other one|the others?|both|isso|aquilo)\b")
DETERMINER_AMBIG = re.compile(r"\b(that|this)\b(?!\s+\w)")     # bare "that"/"this" (not followed by a word)
ES_EL_PRONOUN = re.compile(r"(?<![a-z])el(?=\s*[,.;!?]|$)")
VAGUE_TIME = re.compile(r"\b(recientes?|recientemente|recently|recent|ultimamente|hace poco|pronto|soon|en breve|shortly|"
                        r"(?:los\s+)?ultimos\s+dias|last\s+few\s+(?:days|weeks|months)|hace\s+unos\s+dias|a\s+few\s+(?:days|weeks)\s+ago|"
                        r"reciente|latest)\b")
RELATIVE_TIME = re.compile(r"\b(hoy|ayer|manana|today|yesterday|tomorrow|esta semana|this week|este mes|this month|"
                           r"proximo|next|pasado|last)\b")
UNRESOLVED_ONES = re.compile(r"\b(los|las|el|la)\s+(anteriores|viejos|viejas|antiguos|antiguas|otros|otras|otro|otra|mismos|mismas)\b|"
                             r"\bthe\s+(previous|old|older|other|same|latest)\s+ones?\b|\bthe\s+(other|previous|same)\s+one\b")
UNIVERSAL = re.compile(r"\b(todo|todos|todas|everything|all)\b(?!\s+(?:the|los|las|el|la)\b)")
GENERIC_OBJ = re.compile(r"\b(archivos?|files?|reportes?|informes?|reports?|documentos?|documents?|registros?|records?)\b")
GENERIC_ANY = re.compile(r"\b(?:el|la|los|las|the)\s+(archivos?|files?|arquivos?|elementos?|items?|cosas?|things?)\b")
DESTRUCTIVE = {"DELETE", "EXECUTE", "UPDATE", "SEND", "DISABLE"}
STOPWORDS = set(("el la los las un una unos unas de del al a en con por para y o e que si se lo the a an of in on to for and or "
                 "with from is are it its please por favor").split())


@dataclass
class Finding:
    field: str
    reason: str
    evidence: str = ""
    confidence: float = 0.9

    def to_dict(self):
        return dict(field=self.field, reason=self.reason, evidence=self.evidence, confidence=self.confidence)


@dataclass
class AmbiguityResult:
    ambiguous: bool
    fields: list = field(default_factory=list)
    reason: str = ""
    findings: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def to_dict(self):
        return dict(ambiguous=self.ambiguous, fields=self.fields, reason=self.reason,
                    findings=[f.to_dict() for f in self.findings], notes=self.notes)


PLURAL_PRON = {"them", "they", "los", "las", "ellos", "ellas", "ambos", "ambas", "those", "these", "both", "eles", "elas", "them"}


_PLURAL: dict = {}


def _noun_positions(s: str) -> dict:
    pos = {}
    for code, rx in legacy.DATA_RX + legacy.ENTITY_RX:
        for m in re.finditer(rx, s):
            if code not in pos:
                pos[code] = m.start()
                quant = re.search(r"\b(?:every|each|all|todos?|todas?|cada|both|ambos|ambas)\s+(?:\w+\s+){0,2}$", s[max(0, m.start() - 24):m.start()])
                _PLURAL[code] = bool(quant) or (m.group().endswith(("s", "es")) and not m.group().endswith(("ss", "us", "is")))
    for m in re.finditer(r"#\w+", s):
        pos.setdefault(m.group(), m.start())
    return pos


def _action_positions(s: str) -> dict:
    pos = {}
    for act, rx in legacy.ACTION_RX + EXTRA_ACTION_RX:
        for m in re.finditer(rx, s):
            pos.setdefault(act, m.start())
    return pos


def detect_ambiguity_graph(text: str, graph: SemanticGraph | None = None) -> AmbiguityResult:
    g = graph or to_graph(text)
    s = strip_accents(text.replace("’", "'"))
    findings: list[Finding] = []
    notes: list = []
    nouns = _noun_positions(s)
    acts = _action_positions(s)
    canon = g.canonical()

    # 1. pronouns without (or with several) antecedents
    pron = [(m.start(), m.group()) for m in PRONOUN_STRICT.finditer(s)] + [(m.start(), m.group()) for m in DETERMINER_AMBIG.finditer(s)]
    pron += [(m.start(), "el") for m in ES_EL_PRONOUN.finditer(s)]
    for word in re.findall(r"[a-z]+", s):                       # enclitic pronouns: "analizalo", "clasificalos"
        m = re.fullmatch(r"([a-z]+?)(lo|la|los|las|le|les|me)", word)
        if m and any(re.search(rx, m.group(1)) for _a, rx in legacy.ACTION_RX + EXTRA_ACTION_RX):
            pron.append((s.find(word), m.group(2)))
    for p, w in pron:
        before = {k for k, v in nouns.items() if v < p and (not k.startswith("#")) and (w in PLURAL_PRON) == _PLURAL.get(k, False)} \
            or {k for k, v in nouns.items() if v < p and k.startswith("#")}
        if not before:
            findings.append(Finding("REFERENCE", "PRONOUN_NO_ANTECEDENT", w, 0.85))
        elif len(before) >= 2:
            findings.append(Finding("REFERENCE", "MULTIPLE_POSSIBLE_REFERENTS", w, 0.8))

    # 2. vague time
    for m in VAGUE_TIME.finditer(s):
        findings.append(Finding("TIME", "VAGUE_TIME", m.group(), 0.55))
    if "AMBIGUOUS_YEAR" in g.meta.get("flags", []):
        findings.append(Finding("TIME", "MISSING_YEAR", ",".join(canon["time"]), 0.95))
    if RELATIVE_TIME.search(s) and not VAGUE_TIME.search(s):
        notes.append({"field": "TIME", "reason": "RELATIVE_TIME_NEEDS_ANCHOR", "severity": "INFO"})

    # 3. unresolved "the old ones", missing target / scope / comparand
    if UNRESOLVED_ONES.search(s):
        findings.append(Finding("REFERENCE", "UNRESOLVED_REFERENT", UNRESOLVED_ONES.search(s).group(), 0.85))
    live = [a for a in canon["actions"]]
    targets = canon["data"] + canon["entities"] + canon["references"] + canon["quantities"]
    if live:
        content = [w for w in re.findall(r"[a-z]{3,}", s) if w not in STOPWORDS
                   and not any(re.fullmatch(rx.replace(r"\b", ""), w) for _a, rx in legacy.ACTION_RX + EXTRA_ACTION_RX)]
        if UNIVERSAL.search(s) and not targets:
            findings.append(Finding("TARGET", "UNSPECIFIED_SCOPE", UNIVERSAL.search(s).group(), 0.8))
        elif not content:
            findings.append(Finding("TARGET", "MISSING_TARGET", "", 0.85))
        if "COMPARE" in live:
            comparands = set(canon["data"]) | set(canon["entities"]) | set(canon["references"]) | set(canon["time"])
            if len(comparands) < 2:
                findings.append(Finding("TARGET", "MISSING_COMPARAND", "", 0.8))
        # 4. destructive action on a generic definite object with no identifier
        if set(live) & DESTRUCTIVE and not canon["negation"]:
            ident = canon["references"] or canon["time"] or re.search(r"[\"“«]", text) or re.search(r"\b(?:de|of|from|del)\s+\w+", s)
            if GENERIC_OBJ.search(s) and not ident and not (set(targets) - set(canon["entities"])):
                findings.append(Finding("REFERENCE", "UNRESOLVED_REFERENT", GENERIC_OBJ.search(s).group(), 0.7))
    if GENERIC_ANY.search(s) and not (canon["references"] or canon["time"] or re.search(r"[\"“«']", text)):
        findings.append(Finding("REFERENCE", "UNRESOLVED_REFERENT", GENERIC_ANY.search(s).group(), 0.7))
    if "AMBIGUOUS_MODALITY" in g.meta.get("flags", []):
        findings.append(Finding("ACTION", "AMBIGUOUS_MODALITY", "permission or request?", 0.8))

    seen, uniq = set(), []
    for f in findings:
        k = (f.field, f.reason)
        if k not in seen:
            seen.add(k); uniq.append(f)
    fields = sorted({f.field for f in uniq})
    return AmbiguityResult(bool(uniq), fields, uniq[0].reason if uniq else "", uniq, notes)
