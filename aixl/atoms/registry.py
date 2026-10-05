"""AIXL 0.4 Concept Registry v0.1 (master prompt §10, §17, §47): the closed, versioned set of concepts, atom types and relations.
A concept is identified by `id`, never by a word. `lex` lists surface forms per language (used by the extractor; they are NOT part of identity).
Anything outside this registry is an EXTENSION concept `x:<english-lemma>` (never mapped to a nearby concept: §21, §51 NO GUESS)."""
REGISTRY_VERSION = "0.4.0"

ATOM_TYPES = {
    "ACTION": "an operation to perform (or not). Carries polarity and modality.",
    "ENTITY": "a thing the action concerns (document, person, file...). Concept id from ENT.* or x:<lemma>.",
    "PROPERTY": "an attribute of an entity or state (confidential, empty, official). PRP.* or x:<lemma>.",
    "QUANTITY": "a number with a mode and unit. value={mode,n,unit}; mode in exact|at_least|at_most|approx|more_than|less_than.",
    "QUANTIFIER": "all|some|each|any|none over an entity.",
    "TIME": "value={rel,ref[,offset]} (offset = duration shifting the ref: '1 month before expiry' = {before, event:expiry, offset:1mo}); rel in before|until|at|after|since|within|every|during ; ref grammar in docs/ATOM_MODEL.md (weekday, today|tomorrow|yesterday, ISO date, <n>h|min|d|w|mo, HH:MM, d<1-31>, jan..dec, (this|next|last)_(week|month|quarter|year|weekend), event:<lemma>).",
    "LOCATION": "a place; concept x:<lemma> or LOC.*.",
    "FORMAT": "an output format (FMT.*).",
    "CONDITION": "container node; value=kind: 'if' (sufficient) | 'only_if' (necessary) | 'whether' (embedded yes/no question). Its body atoms carry scope=<condition id>.",
    "REFERENCE": "an anaphor/deictic (it, the same, another): value=kind: 'prev' (it/them) | 'other' (another).",
    "NAME": "a proper name (person, org); value=the name.",
}
MODALITIES = ("DO", "DONT", "MAY", "ADVISE", "DISCOURAGE", "NOT_REQUIRED")   # on ACTION; default DO
POLARITIES = ("+", "-")                                                         # on PROPERTY/ENTITY inside conditions; default +

RELATIONS = {
    "TARGETS": "ACTION -> ENTITY|NAME|REFERENCE: what the action applies to",
    "RECIPIENT": "ACTION -> ENTITY|NAME: who receives",
    "AGENT": "ACTION -> ENTITY|NAME: who must do it (only when stated)",
    "SOURCE": "ACTION|ENTITY -> ENTITY|NAME|LOCATION|FORMAT: where it comes from ('from X', 'from Excel')",
    "HAS_PROPERTY": "ENTITY -> PROPERTY",
    "QUANTIFIED_BY": "ENTITY -> QUANTIFIER",
    "CONSTRAINED_BY": "ACTION|ENTITY -> QUANTITY (limit on the action's result or on the entity count)",
    "OUTPUT_AS": "ACTION -> FORMAT",
    "OCCURS_AT": "ACTION|ENTITY|PROPERTY -> TIME (a time on an entity: 'tickets closed since last quarter' = ticket HAS_PROPERTY closed, closed OCCURS_AT since last_quarter)",
    "LOCATED_AT": "ACTION|ENTITY -> LOCATION",
    "CONDITIONED_BY": "ACTION -> CONDITION",
    "EXCLUDES": "ENTITY -> ENTITY: the second entity node is the excluded subset ('all documents except confidential ones')",
    "RESTRICTS_TO": "ENTITY -> ENTITY: second node is the only allowed subset ('only the confidential ones')",
    "PRECEDES": "ACTION -> ACTION: first must happen before second",
    "OF": "ENTITY -> ENTITY|NAME|REFERENCE: complement / possessive / apposition / purpose ('contract of the lease', 'Marta's quote', 'customer Rodrigues', 'bio for Dr. Okafor')",
    "RESULTS_IN": "ACTION -> PROPERTY|ENTITY|NAME|LOCATION: the state, form or language the action produces ('into French', 'as reconciled', 'in red', 'into one spreadsheet')",
    "CONTENT": "ACTION -> ACTION: the action that is the content of a request/reminder/delegation ('remind me TO PAY', 'ask Rafael TO REVIEW', 'help me PLAN')",
    "PURPOSE": "ACTION -> ACTION: the action done so that another can happen ('so the client sees why')",
    "DESTINATION": "ACTION|ENTITY -> ENTITY|NAME|LOCATION|FORMAT: where it goes / what it is converted into ('to Cartagena', 'to JSON')",
    "USING": "ACTION -> ENTITY|PROPERTY: instrument / means ('tag with the event date', 'pay with the corporate card')",
    "REFERS_TO": "REFERENCE -> ENTITY|ACTION",
}

_A, _E, _P, _Q, _T, _L, _F, _C, _R, _N, _QF = "ACTION", "ENTITY", "PROPERTY", "QUANTITY", "TIME", "LOCATION", "FORMAT", "CONDITION", "REFERENCE", "NAME", "QUANTIFIER"
RELATION_SIG = {   # relation -> (allowed source types, allowed target types): enforced by AtomGraph.validate()
    "TARGETS": ({_A}, {_E, _N, _R, _C, _L}), "RECIPIENT": ({_A}, {_E, _N, _R}), "AGENT": ({_A}, {_E, _N, _R}), "SOURCE": ({_A, _E}, {_E, _N, _L, _R, _F}),
    "CONTENT": ({_A}, {_A}), "PURPOSE": ({_A}, {_A}), "DESTINATION": ({_A, _E}, {_E, _N, _L, _R, _F}),
    "HAS_PROPERTY": ({_E, _N, _R}, {_P}), "QUANTIFIED_BY": ({_E, _N}, {_QF}), "CONSTRAINED_BY": ({_A, _E}, {_Q}), "OUTPUT_AS": ({_A}, {_F}),
    "OCCURS_AT": ({_A, _E, _P}, {_T}), "LOCATED_AT": ({_A, _E}, {_L, _E, _N, _R}), "CONDITIONED_BY": ({_A}, {_C}), "EXCLUDES": ({_E}, {_E}), "RESTRICTS_TO": ({_E}, {_E}),
    "PRECEDES": ({_A}, {_A}), "REFERS_TO": ({_R}, {_E, _A, _N, _R}), "OF": ({_E}, {_E, _N, _R}), "RESULTS_IN": ({_A}, {_P, _E, _N, _L, _F, _Q}), "USING": ({_A}, {_E, _P}),
}

def _c(id, type_, definition, lex, parent=None, near=(), non=()):
    return dict(id=id, type=type_, definition=definition, lex=lex, parent=parent, near=list(near), non_examples=list(non))

ACT = lambda k, d, es, en, pt, **kw: _c("ACT." + k, "ACTION", d, dict(es=es, en=en, pt=pt), **kw)
ENT = lambda k, d, es, en, pt, **kw: _c("ENT." + k, "ENTITY", d, dict(es=es, en=en, pt=pt), **kw)
PRP = lambda k, d, es, en, pt, **kw: _c("PRP." + k, "PROPERTY", d, dict(es=es, en=en, pt=pt), **kw)
FMT = lambda k, d, *forms: _c("FMT." + k, "FORMAT", d, dict(es=list(forms), en=list(forms), pt=list(forms)))

CONCEPTS = [
    # ---- actions (stems; matched as prefixes by the extractor) ----
    ACT("SUMMARIZE", "produce a shorter version keeping the main points", ["resum", "sintetiz"], ["summariz", "summaris"], ["resum", "sintetiz"], near=["ACT.EXTRACT"]),
    ACT("TRANSLATE", "render text in another language", ["traduc", "traduz"], ["translat"], ["traduz", "traduc"]),
    ACT("SEND", "transmit something to a recipient", ["envi", "mand", "remit"], ["send", "mail", "forward"], ["envi", "mand"], near=["ACT.PUBLISH"]),
    ACT("DELETE", "remove permanently", ["elimin", "borr", "suprim"], ["delet", "remov", "erase", "purg"], ["elimin", "apag", "delet", "remov"]),
    ACT("CREATE", "make something new", ["cre", "genera", "elabor", "redact", "escrib"], ["creat", "generat", "make", "draft", "write"], ["cri", "gera", "elabor", "redij", "escrev"]),
    ACT("UPDATE", "modify existing content", ["actualiz", "modific"], ["updat", "modif", "edit"], ["atualiz", "modific", "edit"]),
    ACT("VERIFY", "check that something holds", ["verific", "comprueb", "valid"], ["verif", "check", "validat"], ["verific", "confer", "valid"]),
    ACT("ANALYZE", "examine to extract insight", ["analiz"], ["analy"], ["analis"]),
    ACT("COMPARE", "contrast two or more things", ["compar"], ["compar", "contrast"], ["compar"]),
    ACT("SEARCH", "look for", ["busc", "encuentr", "localiz"], ["search", "find", "look"], ["busc", "encontr", "procur", "localiz"]),
    ACT("EXTRACT", "pull specific parts out", ["extra"], ["extract"], ["extra"]),
    ACT("CLASSIFY", "assign categories", ["clasific", "categoriz"], ["classif", "categoriz", "categoris"], ["classific", "categoriz"]),
    ACT("CALCULATE", "compute a numeric result", ["calcul"], ["calculat", "comput"], ["calcul"]),
    ACT("REQUEST", "ask someone for something", ["solicit", "pid", "ped"], ["request", "ask"], ["solicit", "peç", "peca", "pedir", "pede"]),
    ACT("NOTIFY", "inform someone", ["notific", "avis", "inform"], ["notif", "inform", "alert", "warn"], ["notific", "avis", "inform"]),
    ACT("APPROVE", "authorize / accept", ["aprueb", "aprob", "autoriz"], ["approv", "authoriz", "authoris"], ["aprov", "autoriz"]),
    ACT("REJECT", "refuse / deny", ["rechaz", "deneg"], ["reject", "deny", "refus", "declin"], ["rejeit", "recus", "neg"]),
    ACT("PUBLISH", "make publicly available", ["public"], ["publish", "post"], ["public"], near=["ACT.SEND"]),
    ACT("SAVE", "store", ["guard", "almacen"], ["sav", "stor"], ["salv", "guard", "armazen"]),
    ACT("COPY", "duplicate", ["copi", "duplic"], ["copy", "duplicat", "clon"], ["copi", "duplic"]),
    ACT("ARCHIVE", "move to long-term storage", ["archiv"], ["archiv"], ["arquiv"]),
    ACT("CANCEL", "stop / annul", ["cancel", "anul"], ["cancel", "annul", "abort"], ["cancel", "anul"]),
    ACT("USE", "employ something", ["us", "utiliz", "emple"], ["use", "utiliz", "employ"], ["us", "utiliz", "empreg"]),
    ACT("INCLUDE", "add as part", ["inclu", "agreg", "anad"], ["includ", "add"], ["inclu", "adicion", "acrescent"]),
    ACT("CALL", "phone someone", ["llam"], ["call", "phone", "ring"], ["lig", "telefon"]),
    ACT("REVIEW", "read critically", ["revis"], ["review", "proofread"], ["revis"]),
    ACT("PAY", "transfer money", ["pag"], ["pay"], ["pag"]),
    ACT("SCHEDULE", "set a time for", ["program", "agend"], ["schedul", "book"], ["program", "agend"]),
    ACT("EXPORT", "write data out to a file/format", ["export"], ["export"], ["export"]),
    ACT("OPEN", "open a file or document", ["abr"], ["open"], ["abr"]),
    ACT("KEEP", "maintain a state/limit on something", ["mant"], ["keep", "maintain"], ["mant"]),
    ACT("REFUND", "return money to someone", ["reembols"], ["refund", "reimburs"], ["reembols"]),
    ACT("ENSURE", "be/have a required property (used when a requirement has no verb: 'the report must be at most 5 pages')", [], [], []),
    ACT("READ", "read", ["lee", "leer", "lea"], ["read"], ["le", "ler"]),
    ACT("SIGN", "sign", ["firm"], ["sign"], ["assin"]),
    ACT("PRINT", "print", ["imprim"], ["print"], ["imprim"]),
    # ---- entities ----
    ENT("SPEAKER", "the person giving the instruction (me, my, nosotros)", ["me", "mi"], ["me", "my"], ["me", "meu"]),
    ENT("PERSON", "an unspecified person or people", ["persona", "personas", "gente"], ["person", "people", "someone"], ["pessoa", "pessoas"]),
    ENT("DOCUMENT", "a generic written document", ["document"], ["document"], ["document"]),
    ENT("REPORT", "a report", ["informe", "reporte"], ["report"], ["relat"]),
    ENT("FILE", "a computer file", ["archivo", "fichero"], ["file"], ["arquivo", "ficheiro"]),
    ENT("EMAIL", "an email message", ["correo", "email", "mail", "e-mail"], ["email", "e-mail", "mail"], ["email", "e-mail"]),
    ENT("MESSAGE", "a message", ["mensaje"], ["message"], ["mensagem"]),
    ENT("INVOICE", "an invoice", ["factura"], ["invoice", "bill"], ["fatura", "nota"]),
    ENT("CUSTOMER", "a customer / client", ["cliente"], ["customer", "client"], ["cliente"]),
    ENT("USER", "a user / account", ["usuario"], ["user"], ["usuario", "usuário"]),
    ENT("EMPLOYEE", "an employee", ["empleado", "trabajador", "funcionario"], ["employee", "worker", "staff"], ["funcion", "empregad"]),
    ENT("SOURCE", "a source of information", ["fuente"], ["source"], ["fonte"]),
    ENT("TEXT", "a piece of text", ["texto"], ["text"], ["texto"]),
    ENT("ORDER", "a purchase order", ["pedido", "orden"], ["order"], ["pedido"]),
    ENT("PAYMENT", "a payment", ["pago"], ["payment"], ["pagamento"]),
    ENT("CONTRACT", "a contract", ["contrato"], ["contract"], ["contrato"]),
    ENT("TICKET", "a support ticket", ["ticket", "incidencia"], ["ticket", "issue"], ["ticket", "chamado"]),
    ENT("RECORD", "a data record / entry", ["registro"], ["record", "entry"], ["registro", "registo"]),
    ENT("IMAGE", "an image", ["imagen", "foto"], ["image", "photo", "picture"], ["imagem", "foto"]),
    ENT("TABLE", "a table of data", ["tabla"], ["table", "spreadsheet"], ["tabela", "planilha"]),
    ENT("PAGE", "a page / web page", ["pagina", "página"], ["page"], ["pagina", "página"]),
    ENT("PASSWORD", "a secret credential", ["contraseña", "clave"], ["password"], ["senha"]),
    ENT("MEETING", "a meeting", ["reunion", "reunión", "cita"], ["meeting", "appointment"], ["reuniao", "reunião"]),
    ENT("BACKUP", "a backup copy", ["respaldo"], ["backup"], ["backup", "copia"]),
    # ---- properties ----
    PRP("CONFIDENTIAL", "marked as not for general disclosure", ["confidencial"], ["confidential"], ["confidencia"], near=["PRP.PRIVATE"]),
    PRP("OFFICIAL", "issued by an authority", ["oficial"], ["official"], ["oficia"]),
    PRP("EMPTY", "contains nothing", ["vacío", "vacio"], ["empty", "blank"], ["vazi"]),
    PRP("PENDING", "not yet done", ["pendiente"], ["pending", "outstanding"], ["pendente"]),
    PRP("URGENT", "needs immediate attention", ["urgente"], ["urgent"], ["urgente"]),
    PRP("PUBLIC", "open to everyone", ["públic", "public"], ["public"], ["public"]),
    PRP("PRIVATE", "restricted to its owner", ["privad"], ["private"], ["privad"]),
    PRP("NEW", "recently created", ["nuevo", "nueva", "nuevos", "nuevas"], ["new"], ["novo", "nova", "novos", "novas"]),
    PRP("OLD", "created long ago", ["antiguo", "viejo", "vieja", "antigua"], ["old"], ["antigo", "velho"]),
    PRP("PAID", "payment completed", ["pagad"], ["paid"], ["pago", "paga"]),
    PRP("DUPLICATE", "repeated copy", ["duplicad"], ["duplicate"], ["duplicad"]),
    PRP("SIGNED", "bearing a signature", ["firmad"], ["signed"], ["assinad"]),
    PRP("INTERNAL", "inside the organization", ["interno", "internos", "interna", "internas"], ["internal"], ["intern"]),
    PRP("EXTERNAL", "outside the organization", ["externo", "externos", "externa", "externas"], ["external"], ["extern"]),
    # ---- formats ----
    FMT("JSON", "JSON", "json"), FMT("CSV", "CSV", "csv"), FMT("PDF", "PDF", "pdf"), FMT("XLSX", "Excel", "excel", "xlsx"),
    FMT("MARKDOWN", "Markdown", "markdown"), FMT("HTML", "HTML", "html"),
]

UNITS = {  # unit id -> surface stems
    "word": ["palabra", "palavra", "word"], "character": ["caracter", "caractere", "character", "char"], "page": ["pagina", "page"],
    "day": ["dia", "day"], "hour": ["hora", "hour"], "minute": ["minuto", "minute"], "week": ["semana", "week"], "month": ["mes", "mese", "month"],
    "item": ["elemento", "item", "elemento", "punto", "bullet", "viñeta"], "line": ["linea", "line", "linha"], "mb": ["mb"],
    "sentence": ["oracion", "frase", "sentence"], "paragraph": ["parrafo", "paragraph", "paragrafo"],
}
WEEKDAYS = {"mon": ["lunes", "monday", "segunda"], "tue": ["martes", "tuesday", "terca"], "wed": ["miercoles", "wednesday", "quarta"],
            "thu": ["jueves", "thursday", "quinta"], "fri": ["viernes", "friday", "sexta"], "sat": ["sabado", "saturday"], "sun": ["domingo", "sunday"]}
RELTIME = {"today": ["hoy", "today", "hoje"], "tomorrow": ["manana", "tomorrow", "amanha"], "yesterday": ["ayer", "yesterday", "ontem"]}

def _load_learned():
    """concepts promoted from data (benchmarks/atoms_mine.py promote): same shape as curated ones, flagged learned=True, English form only, never used by the rule extractor."""
    import json
    import os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "learned_concepts.json")
    if not os.path.exists(p): return []
    out = []
    for r in json.load(open(p, encoding="utf-8")):
        words = [w for w in r["lemma"].split("_") if w]
        c = _c(r["id"], r["type"], r["definition"], dict(es=[], en=[" ".join(words)], pt=[]))
        c["learned"] = True; c["evidence"] = r.get("evidence", {})
        out.append(c)
    return out


LEARNED = _load_learned()
CONCEPTS.extend(LEARNED)
_BY_ID = {c["id"]: c for c in CONCEPTS}

def concept(cid: str):
    return _BY_ID.get(cid)

def is_known(cid: str) -> bool:
    return cid in _BY_ID or cid.startswith("x:")

def registry_dict() -> dict:
    return dict(version=REGISTRY_VERSION, atom_types=ATOM_TYPES, modalities=MODALITIES, relations=RELATIONS, concepts=CONCEPTS, units=sorted(UNITS))
