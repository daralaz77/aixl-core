"""Critical-slot INVARIANTS: what must survive a hop, checked WITHOUT understanding the nouns.

Equivalence needs a vocabulary; preservation of the critical slots does not. A relay can paraphrase every noun and still be faithful, but it must not lose a
negation, change a number / date / time / unit, flip a modality (`must`->`may`), turn `and` into `or`, move a weekday, drop a condition or a clause, or swap a
named entity. Those slots are closed-class words, digits and capitalised tokens: they are extracted deterministically in ES/EN/PT, language-independent codes.

`extract(text)` -> {family: frozenset(slot)}.  `check(source, relay)` -> violations (family, only_in_source, only_in_relay).
It makes NO claim of equivalence: no violation means "no critical slot visibly changed", never "same meaning". Families are measured, not assumed:
benchmarks/invariants_eval.py reports per-family recall / false-alarm on labelled pairs of other authors."""
import collections
import re

from aixl.core.limits import check_size
from aixl.core.normalizer import strip_accents
from aixl.core.numberwords import canonical_numbers
from aixl.translators.auto import to_graph_auto

# constraint prefix -> family. Everything else (entities, data, actions) is vocabulary-dependent and deliberately NOT an invariant.
_FAMILY = {
    "CMP": "COMPARATOR", "COND": "CONDITION", "DISJ": "DISJUNCTION", "DOW": "WEEKDAY", "DOWREL": "WEEKDAY_RELATION", "DAYM": "DAY_OF_MONTH",
    "TIME_AT": "CLOCK", "TIME_BETWEEN": "CLOCK", "BEFORE": "CLOCK", "AFTER": "CLOCK", "MEAS": "UNIT", "PER": "UNIT", "MODAL": "MODALITY", "NEGN": "NEGATION",
    "NEGW": "NEGATION", "ONLY": "ONLY", "FREQ": "FREQUENCY", "CLAUSES": "CLAUSES", "MOD": "MODIFIER", "QTY": "QUANTITY", "AGE>": "AGE", "AGE<": "AGE",
    "SEQ": "SEQUENCE", "FORBID_": "NEGATION", "ALLOW_": "PERMISSION",
}
_NAME = re.compile(r"(?<![\w@#])(?:@[A-Za-z0-9_.]+|#\d+|[\w.+-]+@[\w-]+\.[\w.-]+|https?://\S+)")
_CAP = re.compile(r"(?<=[\s,;:(])([A-ZÁÉÍÓÚÑ][\wáéíóúñ]{2,})")        # capitalised word NOT at the start of a sentence
_WORD = re.compile(r"[a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00e3\u00f5\u00e7]+")
# `la` / `lo` are left out on purpose: they are mostly ARTICLES in Spanish (`de la tarde`, `lo importante`), so counting them made `6 de la tarde` -> `18:00` a "pronoun change".
_PRONOUNS = frozenset("he she him her his hers they them their theirs it its \u00e9l ella ellos ellas le les su sus ele ela eles elas dele dela deles delas seu sua seus suas".split())
_SECOND = re.compile(r"(?<![a-z])(?:you|your|yours|te|ti|tu|tus|usted|ustedes|voce|voces|vos)(?![a-z])")
_DELEGATE = frozenset("have ask tell request instruct pide pidele pideles dile diles pedile pede peca diga diz solicita".split())
_NUM = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?![\w])")


def _family_of(constraint: str):
    for pre, fam in _FAMILY.items():
        if constraint.startswith(pre):
            return fam
    return None


_BOUND = frozenset("more less fewer greater higher lower better worse equal above below older newer earlier later mas menos mayor menor superior inferior igual mais maior anterior posterior".split())


def _is_pt(text: str) -> bool:
    from aixl.translators.natural_to_semantic import _PT_CUE
    return bool(_PT_CUE.search(strip_accents(text).lower()) or re.search(r"[\u00e3\u00f5\u00e7]", text.lower()))


def _or_count(text: str, pt: bool) -> int:
    """or / ou / u, and the Spanish `o` (but not the Portuguese article `o`, and not `or more`): decided once for the pair, see `check`."""
    toks = re.findall(r"(?<![a-z0-9])[a-z]+(?![a-z0-9])", strip_accents(text).lower())
    return sum(1 for i, t in enumerate(toks)
               if (t in ("or", "ou", "u") or (t == "o" and not pt and i > 0 and toks[i - 1] not in ("e", "y", "ou", "or"))) and not (i + 1 < len(toks) and toks[i + 1] in _BOUND))


_LEAD = re.compile(r"^(?:siempre y cuando|siempre y que|siempre que|provided that|as long as|desde que|contanto que|sempre que|once|as soon as|en cuanto|assim que|when|whenever|if|unless|cuando|quando|si|se)\s+")


_ARTICLES = frozenset("the a an el la los las un una lo o os as um uma".split())


def _strip_connective(clause: str) -> str:
    """The condition text without the word that introduces it: `siempre que X` == `siempre y cuando X` == `X`."""
    prev = None
    while prev != clause:
        prev, clause = clause, _LEAD.sub("", clause.strip())
    return " ".join(w for w in clause.split() if w not in _ARTICLES)         # `all regression tests` == `all the regression tests`


# USE_LIMIT: the markers that say how / by whom / in what state the information may be used (`Confidential.`, `under NDA`, `Embargoed`, `for management`, `Draft`).
# They carry no negation, number, date or modal, so no other family sees them go. Closed-class lexicon, ES/EN/PT, matched on accent-stripped lowercase tokens and COARSE
# concepts on purpose: `confidential` -> `internal-use document` keeps the concept and is not a change; dropping the concept, adding one, or swapping it for another is.
# Presence only: the family does not say WHICH audience (`for management` -> `for the board` is the same concept), see LIMITATIONS.md E-USE-LIMIT.
_AUD_NOUN = (r"team|teams|managers?|management|committee|board|auditors?|executives?|directors?|leadership|c ?suite|council|"
             r"equipos?|equipes?|comite|gerencia|gerentes?|junta|directiva|directivos?|diretoria|diretores?|auditores|ejecutivos?|executivos?|"
             r"conselho|consejo|administracion|administracao|jefaturas?|chefias?|lideranca|liderazgo|cupula|alta direccion|alta direcao")
_AUD_TERMS = r"(?:(?:[a-z]+\s+){0,2}(?:" + _AUD_NOUN + r")(?:\s+(?:de|da|do|of)\s+[a-z]+)?)"
# constructions that make a group the AUDIENCE of a document (not its recipient): `written for`, `addressed to`, `dirigido a`, `voltado aos`, `reserved for`...
_AUD_VERB = (r"(?:reserved for|intended for|written for|prepared for|drafted for|meant for|made for|tailored for|aimed at|targeted at|geared to|geared towards|addressed to|directed to|oriented to|"
             r"reservad[oa]s? (?:para|al?|a la|a los|a las)|exclusiv[oa]s? (?:para|de)|destinad[oa]s? (?:al?|a la|a los|a las|para|aos|as|ao)|dirigid[oa]s? (?:al?|a la|a los|a las|para)|escrit[oa]s? para|redactad[oa]s? para|preparad[oa]s? para|elaborad[oa]s? para|"
             r"orientad[oa]s? (?:al?|a la|a los|a las|para|aos|as|ao)|pensad[oa]s? para|enfocad[oa]s? (?:al?|a la|a los|a las|en|para)|redigid[oa]s? para|voltad[oa]s? (?:a|aos|as|ao|para)|direcionad[oa]s? (?:a|aos|as|ao|para)|"
             r"dirigid[oa]s? (?:aos|as|ao)|escritos? para|exclusive to|exclusivo para)")
_USE_LIMIT_PATTERNS = {
    "CONFIDENTIALITY": r"confidential\w*|confidencial\w*|privileged|privilegiad\w*|classified|clasificad\w*|classificad\w*|restricted|restringid\w*|restrit\w*|reservad\w*(?!\s+(?:para|al?|ao|aos|as)\b)|"
                       r"internal|internos?|internas?|in house|sensitive|sensible\w*|sensivel|sensiveis|sigilos\w*|sigilo|nda|non disclosure|under seal|bajo sello|sob sigilo|em sigilo|"
                       r"segredo de justica|secreto de sumario|"
                       r"acuerdos? de confidencialidad|acordos? de confidencialidade|confidentiality agreements?|uso interno|use internal",
    "LEGAL_HOLD": r"embargo\w*|legal review|revision legal|revision juridica|revisao juridica|under legal|sub judice|subject to contract|sujet[oa]s? a (?:contrato|revision \w+|aprobacion legal)|"
                  r"sujeit[oa]s? a (?:contrato|parecer \w+|revisao \w+|aprovacao \w+)|pending court|orden judicial|ordem judicial|court order|bajo reserva legal|legal hold|"
                  r"in litigation|under litigation|en litigio|en proceso judicial|em litigio|sob litigio|em juizo|aguardando decisao \w+|pendiente de (?:decision|sentencia) \w+|pending (?:a )?(?:court|judicial|legal) \w+|"
                  r"parecer juridico|bajo investigacion|sob investigacao|under investigation",
    "AUDIENCE": r"" + _AUD_VERB + r"\s+(?:(?:the|our|your|la|el|los|las|nuestra|nuestro|a|o|os|as|a nossa|o nosso)\s+)?" + _AUD_TERMS + r"|"
                r"(?<![a-z])for\s+(?:the\s+)?" + _AUD_TERMS + r"\s+eyes|"
                r"(?:para|por)\s+(?:los\s+)?ojos\s+de\s+" + _AUD_TERMS,
    "DOC_STATUS": r"drafts?|borrador(?:es)?|rascunhos?|minutas?|esbocos?|boceto|preliminar(?:y|es)?|provisional\w*|provisori\w*|unverified|sin verificar|sem verificar|unconfirmed|sin confirmar|"
                  r"work in progress|wip|trabajo en curso|em andamento|em elaboracao|en elaboracion|pending approval|pendiente de aprobacion|pendente de aprovacao|"
                  r"under review|en revision|em revisao|em analise|sob analise|en analisis|not final|no definitiv\w*|nao definitiv\w*|"
                  r"em fase de (?:aprovacao|revisao|analise|elaboracao)|en fase de (?:aprobacion|revision|analisis|elaboracion)|in (?:approval|review) phase|"
                  r"awaiting (?:approval|sign off)|aguardando (?:aprovacao|validacao)|a la espera de (?:aprobacion|validacion)|pendiente de (?:validacion|revision)",
}
_USE_LIMIT_RE = {k: re.compile(r"(?<![a-z])(?:" + v + r")(?![a-z])") for k, v in _USE_LIMIT_PATTERNS.items()}
_AUD_LABEL = re.compile(r"(?:^|[.;:(—-])\s*(?:for|para)\s+(?:(?:the|la|el|los|las|a|o|os|as)\s+)?" + _AUD_TERMS + r"\s*[.)]?\s*$")


# v5 (2026-10-29): a STRONG audience verb is itself the marker, whatever group follows (`written for investors`, `dirigido a los profesores`, `aimed at interns`): any group can be an audience, so the noun list
# can never be closed. The risk is `prepared for the meeting` / `escrito para el viernes`: the complement is an EVENT, a deadline, a number or a verb, not an audience, so those are excluded.
_NOT_AUDIENCE = frozenset((
    "meeting meetings review reviews launch launches release releases demo demos presentation presentations call calls deadline deadlines audit audits trip trips event events workshop workshops "
    "training session sessions sprint quarter season hearing hearings trial test tests testing upgrade migration negotiation negotiations interview interviews conference kickoff visit visits "
    "inspection rollout deployment handover closing close project projects task tasks purpose use case occasion day days week weeks month months year years morning afternoon evening night "
    "reunion reuniones revision lanzamiento estreno presentacion presentaciones llamada fecha auditoria viaje evento eventos taller capacitacion sesion trimestre cierre prueba pruebas migracion "
    "negociacion entrevista conferencia visita inspeccion despliegue entrega proyecto tarea uso dia dias semana semanas mes meses ano anos manana tarde noche "
    "reuniao reunioes revisao lancamento apresentacao apresentacoes ligacao prazo viagem oficina treinamento sessao fechamento teste testes negociacao conferencia inspecao implantacao tarefa "
    "uso semana mes ano amanha noite hoje ontem hoy ayer today tomorrow yesterday tonight now soon later next last this that these those it them him her one each every any all "
    "lunes martes miercoles jueves viernes sabado domingo monday tuesday wednesday thursday friday saturday sunday segunda terca quarta quinta sexta "
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre january february april june july august september october november december "
    "janeiro fevereiro marco maio junho julho setembro outubro novembro dezembro "
    "fair fairs phase phases campaign campaigns rehearsal rehearsals drill drills shift shifts period periods round rounds seminar seminars cycle cycles cutover go live freeze window windows "
    "feria ferias fase fases campana campanas ensayo ensayos simulacro simulacros turno turnos periodo periodos ronda rondas seminario seminarios ciclo ciclos jornada jornadas renovacion "
    "renegociacion migracion migraciones implementacion congelamiento ventana "
    "feira feiras campanha campanhas ensaio ensaios simulado turno turnos periodo periodos rodada rodadas seminario seminarios ciclo ciclos jornada jornadas renovacao renegociacao "
    "migracao migracoes implementacao relancamento plantao mutirao congelamento janela").split())
# technical TARGETS (`pull request targeting the main branch` / `dirigido a la rama principal`): a place in a system, not an audience (found on blind11: 1 false alarm on an equivalent pair)
_TECH_TARGET = frozenset(("branch branches repo repository repositories folder folders directory file files server servers environment environments endpoint endpoints table tables column columns "
                         "module modules service services database databases cluster clusters platform platforms system systems rama ramas repositorio repositorios carpeta carpetas archivo archivos "
                         "servidor servidores entorno entornos tabla tablas columna columnas modulo modulos servicio servicios plataforma plataformas sistema sistemas pasta pastas arquivo arquivos "
                         "servidores ambiente ambientes tabela tabelas coluna colunas servico servicos plataformas ramificacao ramificacoes pipeline pipelines experiment experiments experimento experimentos pilot pilots piloto pilotos prototype prototype prototipo").split())
_DET = frozenset("the our your their his her its a an this that these those el la los las un una unos unas lo nuestro nuestra nuestros nuestras su sus mi tu o os as um uma uns umas seu sua seus suas nosso nossa nossos nossas".split())
_STRONG = re.compile(r"(?<![a-z])" + _AUD_VERB + r"\s+(?P<rest>[a-z]+(?:\s+[a-z]+){0,3})")


_ROMANCE_VERB = re.compile(r"(?:dirigid|destinad|orientad|enfocad|pensad|escrit|redactad|redigid|voltad|direcionad|preparad|elaborad|reservad|exclusiv)[oa]|\bpara\b|\bpra\b")
_ING_NOUNS = frozenset("marketing engineering accounting advertising banking nursing housing consulting publishing manufacturing meeting building".split())
_NP_END = frozenset(("and or to in on with for by that which while so then but when if before after at from y e u ou con com que para pra por en em na cuando quando si se donde onde de del da do of").split()) - frozenset(("de", "del", "da", "do", "of"))


def _strong_audience(lw: str) -> bool:
    """A STRONG audience verb + a complement that is an audience. The complement is the noun phrase after the verb: English puts its HEAD last (`the quarterly business review`), Spanish/Portuguese first
    (`la feria comercial`), so both ends are checked against the event / time / technical-target lists; a gerund or an infinitive head (`meant for testing`, `escrito para revisar`) is a purpose, not an audience."""
    for m in _STRONG.finditer(lw):
        toks = m.group("rest").split()
        i = 0
        while i < len(toks) - 1 and toks[i] in _DET:
            i += 1
        np = []
        for t in toks[i:]:
            if t in _NP_END:
                break
            np.append(t)
        if not np:
            continue
        first, last = np[0], np[-1]
        if any(t in _TECH_TARGET for t in np) or first in _NOT_AUDIENCE or last in _NOT_AUDIENCE or len(first) < 3 or first in _DET:
            continue                                                  # `prepared for the meeting`, `targeting the main branch`, `written for tomorrow`
        if (first.endswith("ing") and first not in _ING_NOUNS) or (last.endswith("ing") and last not in _ING_NOUNS):
            continue                                                  # `aimed at reducing churn`, `meant for load testing`: a gerund starts the complement or is its head = a purpose
        if len(first) > 4 and first.endswith(("ar", "er", "ir")) and _ROMANCE_VERB.search(m.group(0)):
            continue                                                  # `orientado a reducir las devoluciones`, `escrito para revisar`: an infinitive = a purpose (Spanish / Portuguese only: `summer` is not a verb)
        return True
    return False


def use_limits(text: str) -> frozenset:
    """The use-limit concepts present in `text` (a subset of CONFIDENTIALITY, LEGAL_HOLD, AUDIENCE, DOC_STATUS)."""
    lw = strip_accents(text).lower().replace("-", " ").replace("\u2011", " ")           # `work-in-progress` == `work in progress`
    found = {k for k, rx in _USE_LIMIT_RE.items() if rx.search(lw)}
    if any(_AUD_LABEL.search(part) for part in re.split(r"(?<=[.!?])\s+", lw.strip())) or _strong_audience(lw):
        found.add("AUDIENCE")
    return frozenset(found)


def extract(text: str, pt: bool | None = None) -> dict:
    check_size(text)
    g = to_graph_auto(text)
    c = g.canonical()
    out: dict = {}
    for k in c["constraints"]:
        fam = _family_of(k)
        if fam and fam != "DISJUNCTION":
            out.setdefault(fam, set()).add(k)
    n_or = _or_count(text, _is_pt(text) if pt is None else pt)
    if n_or:
        out["DISJUNCTION"] = {f"DISJ={n_or}"}
    if c.get("negation"):
        out.setdefault("NEGATION", set()).add("NEG")
    conds = {_strip_connective(x) for x in c.get("conditions", ()) if x}
    if conds:
        out["CONDITION_TEXT"] = conds                            # WHAT the condition says (`incident is critical` -> `incident is minor`), not only which connective introduces it
    for t in c.get("time", ()):
        out.setdefault("DATE", set()).add(str(t))
    for q in c.get("quantities", ()):
        out.setdefault("QUANTITY", set()).add(str(q))
    text = text.strip()
    caps = {m.group(1).lower() for m in _CAP.finditer(text) if text[:m.start()].rstrip()[-1:] not in ("", ".", "!", "?", "\u00bf", "\u00a1", "*", '"', "\u201c", "\u2018", "'", ">", "-", "\u2022", "#")}
    names = {m.group(0).lower() for m in _NAME.finditer(text)} | caps
    acts = set(c.get("actions") or ())
    if acts:
        out["ACTION"] = acts                                     # the lexicon's verbs: `send` -> `cancel` is a different action
    order = tuple(m.group(0).lower() for m in sorted(list(_NAME.finditer(text)) + [m for m in _CAP.finditer(text) if m.group(1).lower() in caps], key=lambda m: m.start()))
    if len(order) >= 2:
        out["NAME_ORDER"] = {order}                              # who comes first: `Ana ... Luis` vs `Luis ... Ana` (role swap)
    lw = strip_accents(text).lower()
    second = [m for m in _SECOND.finditer(lw)]
    if second:
        order = tuple(x for _p, x in sorted([(m.start(), m.group(0)) for m in list(_NAME.finditer(text))] + [(m.start(), m.group(1).lower()) for m in _CAP.finditer(text) if m.group(1).lower() in caps]
                                           + [(m.start(), "you") for m in second]))
        if len(order) >= 2:
            out["NAME_ORDER"] = {order}                          # the addressee (`you`, `te`, `voce`) moves too: `assign it to the team` -> `assign it to you`
    pron = collections.Counter([w for w in _WORD.findall(text.lower()) if w in _PRONOUNS] + ["you" for _m in second])
    if pron:
        out["PRONOUN"] = {f"{k}:{v}" for k, v in pron.items()}     # `he`/`she`, `él`/`ella`, `his`/`her`: whom a pronoun points to
    if names:
        out["NAME"] = names
    nums = canonical_numbers(text)                              # digits, number words (`catorce` = 14) and clock times (`6 pm` = `18:00`) in one notation
    if nums:
        out["NUMBER"] = nums
    toks = re.findall(r"[a-z]+", lw)
    deleg = collections.Counter(t for t in toks if t in _DELEGATE)
    if deleg:
        out["DELEGATION"] = {f"n:{sum(deleg.values())}"}                   # `Send Priya the budget` -> `Have Priya send it`: who acts changed (`solicita` = `pede`: the total, not the cue)
    ul = use_limits(text)
    if ul:
        out["USE_LIMIT"] = set(ul)                             # `Confidential.` / `under NDA` / `Embargoed` / `for management` / `Draft`: what limits the use of the content
    dos = sum(1 for w in _WORD.findall(text.lower()) if w == "dos")
    if dos:
        out["AMBIGUOUS"] = {f"dos:{dos}"}                       # ES "two" / PT "of the": the count must not change
    return {k: frozenset(v) for k, v in out.items()}


def check(source: str, relay: str, families=None) -> list:
    """Violations between a source text and its relay: [(family, only_in_source, only_in_relay)] for each family whose slot sets differ."""
    pt = _is_pt(source) or _is_pt(relay)                           # one language for the pair
    a, b = extract(source, pt), extract(relay, pt)
    out = []
    for fam in sorted(set(a) | set(b)):
        if families is not None and fam not in families:
            continue
        sa, sb = a.get(fam, frozenset()), b.get(fam, frozenset())
        if fam == "CONDITION_TEXT" and (not sa or not sb):
            continue                                              # one side has no condition TEXT (`once X` was not captured): a dropped condition is the CONDITION family's job
        if sa != sb:
            out.append((fam, tuple(sorted(sa - sb)), tuple(sorted(sb - sa))))
    return out


# Families that flag a corruption without flagging benign near-verbatim edits (selection rule and numbers: benchmarks/invariants_relay_eval.py, LIMITATIONS.md E-RELAY).
RELAY_FAMILIES_V1 = frozenset({"ACTION", "AMBIGUOUS", "CONDITION_TEXT", "DELEGATION", "NAME_ORDER", "PRONOUN", "CLAUSES", "COMPARATOR", "CONDITION", "DATE", "DISJUNCTION", "MODALITY", "MODIFIER", "NAME", "NEGATION", "NUMBER", "ONLY", "QUANTITY", "SEQUENCE", "WEEKDAY"})
RELAY_FAMILIES = RELAY_FAMILIES_V1 | {"USE_LIMIT"}      # V1 = before the use-limit family (kept so a baseline can be re-scored)


def relay_check(source: str, relay: str) -> dict:
    """Did a critical slot change between `source` and its `relay`?  Built for NEAR-VERBATIM relays (copy, truncation, a flipped word, an injected
    clause). It is NOT an equivalence test: `ok: true` means "no critical slot visibly changed", never "same meaning" — a rewording that moves a negation
    into a different construction can raise a violation, and an antonym swap (`send` -> `cancel`) or a vocabulary-only change is invisible to it.
    Measured (other authors' seeds, families chosen on the project's own): 94.6 % of meaning-changing corruptions flagged, 0.0 % of benign edits flagged."""
    try:
        v = check(source, relay, RELAY_FAMILIES)
    except Exception as e:                                        # noqa: BLE001 — fail closed: an input we cannot analyse is not "ok"
        return {"ok": False, "violations": [], "reason": f"not analysed: {type(e).__name__}", "regime": "near-verbatim relay"}
    return {"ok": not v, "regime": "near-verbatim relay",
            "violations": [{"family": f, "only_in_source": list(a), "only_in_relay": list(b)} for f, a, b in v],
            "note": "ok:true = no critical slot visibly changed; it is not a proof of equivalence"}
