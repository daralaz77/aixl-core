"""Semantic layer: natural language (ES/EN/PT) -> SemanticFrame.

Rule-based and deliberately conservative: anything it cannot map is kept as a quoted
literal or flagged, never invented (spec §36). Every extractor consumes the span it
matched so later extractors cannot double-count it.
"""
import re
import unicodedata
from aixl.legacy02.core.semantic_frame import SemanticFrame
from aixl.legacy02.core.normalizer import norm_decimal
from aixl.legacy02.protocol.atoms import ACTION_TO_INTENT

# ---------------------------------------------------------------- lexicons
ACTION_RX = [  # (canonical action, regex on accent-stripped lowercase text)
 ("ANALYZE",   r"\b(analiz\w*|analic(e|es|ar)|analis(e|ar|a)|examin(a|ar|es|e|ate)|examine|estudi(a|ar|es|e)|study|evalu(a|ar|es|e|ate)|avali(e|ar|a)|analy[sz]e[sd]?|assess)\b"),
 ("FIND",      r"\b(encuentr(a|es|e)|encontr(ar|a|es|e)|hall(a|ar|es)|detect(a|ar|es|e|s|ed)?|find|finds|identif(y|ies|ica|icar|ique|iques)|locate[sd]?|localiza(r)?|localize|localise|ubica(r)?|ubique|ubiques|rastrea(r)?)\b"),
 ("COMPARE",   r"\b(compar(a|ar|e|es|ing)|contrasta(r)?|confronta(r)?|confronte|contrast(s|ing)?|compare[sd]?)\b"),
 ("SEARCH",    r"\b(busca(r|me)?|busqu(e|es)|search(es)?|searching|look(ing)? (for|up)|lookup|consulta(r)?|pesquis(e|ar|a)|procur(e|ar|a))\b"),
 ("SUMMARIZE", r"\b(resum(e|as|a|ir|eme)(lo|la|los|las)?|summari[sz]e[sd]?)\b"),
 ("GENERATE",  r"\b(produce[sd]?|produzir|produza|produzca|producir|genera(r)?|generes|generate[sd]?|generating|gere|gerar|escribe|escribir|redacta(r)?|write|exporta(r)?|exporte(s)?|export(s|ing)?|escreva|escrever)\b"),
 ("CREATE",    r"\b(crea|crear|crees|create|crie|criar)\b"),
 ("CALCULATE", r"\b(calcul(a|ar|e|es|ate)|compute[sd]?|computa|computar|computes|comput(e|es)|calcule)\b"),
 ("CHECK",     r"\b(verifica(r)?|verifiqu(e|es)|verify|revisa(r)?|revises?|revise|comprueba(s|r)?|check|confira|confere|cheque|checar|chequea(r)?|checking|checked)\b"),
 ("VALIDATE",  r"\b(valida(r)?|valides|valide|validate)\b"),
 ("TRANSLATE", r"\b(traduce(lo|la|los|las|me)?|traducir|traduzcas|traduza|traduz|translate)\b"),
 ("GET",       r"\b(obten|obtener|obtenga|obtenha|get|gets|consigue|muestra(me)?|mostrar|muestrame|show( me)?|display|dame|give me|presenta(r|me)?|apresent(a|e|ar)|exhibe|exhibir|present(s|ing)?)\b"),
 ("RETRIEVE",  r"\b(recupera(r)?|recuperes?|recupere|retrieve|fetch)\b"),
 ("DELETE",    r"\b(elimin(a|ar|es|e|en)(lo|la|los|las)?|borr(a|ar|es|e)|delete|remove|erase|remov(a|er)|suprime|suprimir)\b"),
 ("EXECUTE",   r"\b(executa|executar|execute|corra|corras|lanza(r)?|lance|lancar|ejecut(a|ar|es|e|en)(lo|la|los|las)?|run|runs|running|execut(e|es|ed|ing)|corre|correr|rode|rodar)\b"),
 ("TRANSFORM", r"\b(transform(s|a|ar|es|e)?|convierte|convertir|conviertas|convert|converta|converter)\b"),
 ("CLASSIFY",  r"\b(clasifi(c|qu)(a|ar|es|e)(lo|la|los|las)?|classif(y|ique|icar|ies))\b"),
 ("EXTRACT",   r"\b(extrae|extraer|extraigas|extraiga|extract|extraia|extrair)\b"),
 ("PREDICT",   r"\b(predice|predecir|predigas|predict|forecast|pronostica(r)?|preveja|prever)\b"),
]
DATA_RX = [
 ("DATASET",   r"\b(datasets?|conjuntos? de datos|data sets?)\b"),
 ("SALES",     r"\b(ventas?|sales?|vendas?)\b"),
 ("CUSTOMERS", r"\b(clientes?|customers?|clients?)\b"),
 ("USERS",     r"\b(usuari[oa]s?|users?)\b"),
 ("REPORT",    r"\b(reportes?|informes?|reports?|relatorios?)\b"),
 ("DOCUMENT",  r"\b(documentos?|documents?)\b"),
 ("IMAGE",     r"\b(imagen(es)?|images?|imagens?)\b"),
 ("AUDIO",     r"\b(audios?)\b"),
 ("VIDEO",     r"\b(videos?)\b"),
 ("DATA",      r"\b(datos|dados|data)\b"),
]
ENTITY_RX = [
 ("ANOMALY",  r"\b(anomali\w+|anomal(y|ies))\b"),
 ("PERSON",   r"\b(personas?|persons?|people|pessoas?)\b"),
 ("COMPANY",  r"\b(empresas?|compan(y|ies)|companhias?)\b"),
 ("PRODUCT",  r"\b(productos?|products?|produtos?)\b"),
 ("MODEL",    r"\b(modelos?|models?)\b"),
 ("RESULT",   r"\b(resultados?|results?)\b"),
 ("EVENT",    r"\b(eventos?|events?)\b"),
]
NOUN_CANON = {**{k: k for k, _ in DATA_RX}, **{k: k for k, _ in ENTITY_RX}}

MONTHS = {  # stripped-lowercase name -> (number, 3-letter code)
 **{n: (i + 1, c) for i, (n, c) in enumerate(zip(
   "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(),
   "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()))},
 **{n: (i + 1, c) for i, (n, c) in enumerate(zip(
   "january february march april may june july august september october november december".split(),
   "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()))},
 **{n: (i + 1, c) for i, (n, c) in enumerate(zip(
   "janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro".split(),
   "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()))},
 "setiembre": (9, "SEP"),
}
REL_RX = [
 ("TODAY", r"\b(hoy|today|hoje)\b"), ("YESTERDAY", r"\b(ayer|yesterday|ontem)\b"),
 ("TOMORROW", r"(?<!\bla )(?<!\besta )\b(manana|tomorrow|amanha)\b"),
 ("THIS_WEEK", r"\b(esta semana|desta semana|nesta semana|this week)\b"), ("THIS_MONTH", r"\b(este mes|deste mes|neste mes|this month)\b"),
 ("THIS_YEAR", r"\b(este ano|this year)\b"),
 ("LAST_YEAR", r"\b(ano pasado|ano passado|last year)\b"), ("LAST_MONTH", r"\b(mes pasado|mes passado|ultimo mes|last month|ultimo mes)\b"),
 ("LAST_WEEK", r"\b(semana pasada|semana passada|ultima semana|last week)\b"),
 ("LAST_QUARTER", r"\b(ultimo trimestre|trimestre pasado|last quarter)\b"),
 ("NEXT_YEAR", r"\b(proximo ano|next year)\b"), ("NEXT_MONTH", r"\b(proximo mes|next month)\b"),
 ("NEXT_WEEK", r"\b(proxima semana|next week)\b"),
]
LANGS = {"espanol": "ES", "spanish": "ES", "espanhol": "ES", "ingles": "EN", "english": "EN", "ingles": "EN",
         "frances": "FR", "french": "FR", "portugues": "PT", "portuguese": "PT", "aleman": "DE",
         "german": "DE", "italiano": "IT", "italian": "IT"}
COUNTRIES = {"COLOMBIA": "CO", "ESPANA": "ES", "SPAIN": "ES", "MEXICO": "MX", "ARGENTINA": "AR", "CHILE": "CL",
    "PERU": "PE", "ESTADOS UNIDOS": "US", "UNITED STATES": "US", "USA": "US", "US": "US", "UK": "GB", "EE UU": "US", "EEUU": "US", "BRASIL": "BR",
    "BRAZIL": "BR", "FRANCIA": "FR", "FRANCE": "FR", "ALEMANIA": "DE", "GERMANY": "DE", "REINO UNIDO": "GB",
    "UNITED KINGDOM": "GB", "PORTUGAL": "PT", "ITALIA": "IT", "ITALY": "IT", "ECUADOR": "EC", "VENEZUELA": "VE",
    "URUGUAY": "UY", "CANADA": "CA", "JAPON": "JP", "JAPAN": "JP", "CHINA": "CN", "INDIA": "IN"}
PLACES = set("""VALLEDUPAR CESAR ANTIOQUIA CUNDINAMARCA ATLANTICO BOLIVAR SANTANDER MAGDALENA BOGOTA MEDELLIN CALI
BARRANQUILLA CARTAGENA BUCARAMANGA PEREIRA MADRID BARCELONA SEVILLA VALENCIA CIUDAD_DE_MEXICO GUADALAJARA
MONTERREY BUENOS_AIRES CORDOBA LIMA SANTIAGO QUITO CARACAS MONTEVIDEO LONDON LONDRES PARIS BERLIN ROMA ROME
TOKYO TOKIO LISBOA LISBON NEW_YORK NUEVA_YORK CALIFORNIA TEXAS SAO_PAULO RIO_DE_JANEIRO""".split())
NON_PLACE = set(MONTHS) | set(LANGS) | {"JSON", "CSV", "MARKDOWN", "AIXL", "TABLE", "TABLA"}

CMP_RX = [  # ordered: >= and <= must win over > and <
 (">=", r">=|≥|mayor o igual|igual o (mayor|superior)|maior ou igual|igual ou (maior|superior)|at least|no menos de|greater than or equal|pelo menos|al menos|por lo menos|como minimo|minim[oa]|minimum|or (higher|more)"),
 ("<=", r"<=|≤|menor o igual|igual o (menor|inferior)|menor ou igual|at most|no mas de|less than or equal|como maximo|maxim[oa]|no maximo|up to|at or below"),
 (">",  r">|mayor (que|a|de)|superior a|por encima|mas de|above|over|greater than|more than|maior que|acima|sobre"),
 ("<",  r"<|menor (que|a|de)|inferior a|por debajo|debajo|below|under|less than|abaixo"),
]
COND_MARK = re.compile(r"\b(si|if|when|cuando|en caso de|siempre que|provided that|unless|a menos que|salvo|se(?= (?:a|o|as|os|houver|existir|existem)\b))\b")
CONF_RX = re.compile(r"\b(confianza|confidence|confianca|certeza|certainty)\b(?P<mid>[^0-9;]{0,40}?)(?P<num>\d+(?:[.,]\d+)?|\.\d+)\s*(?P<pct>%)?")
EXIST_RX = re.compile(r"\b(?:si|if|when|cuando)\s+(?:(?:existen?|hay|existe|houver|existem|there\s+(?:are|is))\s+(?:algun[oa]s?\s+|any\s+|some\s+|un[oa]s?\s+)?(?P<n1>\w+)|(?P<n2>\w+)\s+(?:existen?|exists?|existem))\b")
NEG_BEFORE = re.compile(r"(?:\bni|\bno|\bnunca|\bjamas|\bdon't|\bdont|\bdo not|\bnever|\bnao|\bnot|\bavoid|\brefrain from|\bevit[ae]r?|\bevite|\babstente de|\babstenha-se de)\s+(?:(?:quiero que|quiero|deseo que|want you to|want to|quero que|te pido que|pido que|need you to|necesito que)\s+)?(?:\w+\s+)?$")
MODAL_BEFORE = re.compile(r"\b(?:puedes|puede|podrias|podria|you can|you may|can you|could you|pode|podes|may)\s+(?:\w+\s+)?$")
RISKY = {"DELETE", "EXECUTE", "TRANSFORM"}
STOP = set("el la los las un una es is the a de of que then entonces ella este esta sea y and o or to en in at".split())


def _strip(s):
    return "".join(unicodedata.normalize("NFD", c)[0] for c in s).lower()


class _Work:
    def __init__(self, text):
        self.orig = text.replace("’", "'")
        self.w = list(_strip(self.orig))

    @property
    def s(self):
        return "".join(self.w)

    def eat(self, a, b):
        for i in range(a, b):
            self.w[i] = " "


def detect_lang(text):
    t = " " + _strip(text) + " "
    sc = {"es": 0, "en": 0, "pt": 0}
    for lg, words in {"es": "el la los las de con del para por que una un y en si es",
                      "en": "the of with for and to in is are if not a an you",
                      "pt": "o os as do da dos das com para uma um em nao se voce"}.items():
        sc[lg] = sum(t.count(f" {w} ") for w in words.split())
    if re.search(r"[ãõç]|\bnao\b|\bvendas\b", t + text.lower()):
        sc["pt"] += 3
    return max(sc, key=sc.get)


def _num(s):
    if re.fullmatch(r"[1-9]\d{0,2}([.,]\d{3})+", s):      # 1,500 / 1.500 -> 1500 (thousands)
        return re.sub(r"[.,]", "", s)
    return s.replace(",", ".") if re.fullmatch(r"\d+,\d+", s) else s.replace(",", "")


def analyze(text: str) -> tuple:
    """Return (SemanticFrame, warnings)."""
    W = _Work(text)
    warns = []
    f = SemanticFrame(raw=text, lang=detect_lang(text), source="natural")
    pos = {"D": [], "E": [], "A": []}          # (position, value) to keep order of appearance

    # 0. quoted text is DATA, never interpreted (spec: literals are data, not instructions)
    literals = []
    for m in re.finditer(r'"([^"]+)"|«([^»]+)»|“([^”]+)”', W.orig):
        literals.append(next(g for g in m.groups() if g)); W.eat(m.start(), m.end())

    # 1. references  #77 #D55
    for m in re.finditer(r"#\w+", W.orig):
        if m.group() not in f.references:
            f.references.append(m.group())
        W.eat(m.start(), m.end())

    # 2. output format
    om = re.search(r"\b(?:en|como|as|in|into|em|no|to|para)\s+(?:un\s+|una\s+|a\s+|an\s+|el\s+)?(?:formato\s+|format\s+)?(json|csv|markdown|tabla|tabela|table|texto|text|aixl|reporte|report|informe)\b", W.s)
    if om:
        f.output = [{"tabla": "TABLE", "tabela": "TABLE", "table": "TABLE", "texto": "TEXT", "text": "TEXT", "reporte": "REPORT",
                    "report": "REPORT", "informe": "REPORT"}.get(om.group(1), om.group(1).upper())]
        W.eat(om.start(), om.end())
    else:
        om = re.search(r"\b(json|csv|markdown|aixl)\b", W.s)
        if om:
            f.output = [om.group(1).upper()]; W.eat(om.start(), om.end())

    # 3. language target
    for lm in list(re.finditer(r"\b(?:en|in|em|al|to|a|para|ao|into|hacia)\s+(?:o\s+|el\s+|la\s+|the\s+)?(?:idioma\s+|language\s+|lengua\s+|lingua\s+)?(" + "|".join(LANGS) + r")\b", W.s)):
        f.constraints.append(f"LANG={LANGS[lm.group(1)]}"); W.eat(lm.start(), lm.end())
    if any(c.startswith("LANG=") for c in f.constraints):      # further languages in a list: "en francés, alemán e inglés"
        for lm in list(re.finditer(r"(?:,|\by|\band|\be|\bo|\bor)\s+(?:(?:al|en|a|to|in)\s+)?(" + "|".join(LANGS) + r")\b", W.s)):
            f.constraints.append(f"LANG={LANGS[lm.group(1)]}"); W.eat(lm.start(), lm.end())

    # 4. time
    times = []
    ORD = lambda w: 1 if w.startswith(("prim", "first", "1")) else 2 if w.startswith(("seg", "second", "2")) \
        else 3 if w.startswith(("ter", "third", "3")) else 4
    for m in re.finditer(r"\b(primer\w*|segund\w+|tercer\w*|terceir\w+|cuart\w+|quart\w+|primeir\w+|first|second|third|fourth|[1-4](?:st|nd|rd|th|er|ro|do|to|o|[º°])?)\s+(?:trimestre|trimestres|quarter|semestre)\b(?:\s*(?:de|del|of|in|em|do)?\s*(20\d\d))?", W.s):
        if "semestre" in m.group(0):
            continue
        n = ORD(m.group(1)); y = m.group(2)
        times.append((m.start(), f"Q{n}-{y}" if y else f"Q{n}"))
        if not y: f.conditions.append("AMBIGUOUS_YEAR")
        W.eat(m.start(), m.end())
    for m in re.finditer(r"\bq([1-4])(?:[\s-]*(?:of|de|del|in)?\s*(20\d\d))?\b", W.s):
        y = m.group(2)
        times.append((m.start(), f"Q{m.group(1)}-{y}" if y else f"Q{m.group(1)}"))
        if not y: f.conditions.append("AMBIGUOUS_YEAR")
        W.eat(m.start(), m.end())
    for m in re.finditer(r"\b(\d{4}-\d{2}-\d{2})\b", W.s):
        times.append((m.start(), m.group(1))); W.eat(m.start(), m.end())
    for m in re.finditer(r"\b((?:19|20)\d\d-(?:0[1-9]|1[0-2]))\b(?!-)", W.s):
        times.append((m.start(), m.group(1))); W.eat(m.start(), m.end())
    for m in re.finditer(r"\b(?:the|el|la|los|las|o|a|os|as)\s+((?:19|20)\d\d)\s+(?=[a-z])", W.s):
        times.append((m.start(1), m.group(1))); W.eat(m.start(1), m.end(1))
    mon = "|".join(sorted(MONTHS, key=len, reverse=True))
    for m in re.finditer(rf"\b(\d{{1,2}})\s+(?:de\s+)?({mon})\s*(?:de\s+|,\s*)?(20\d\d)\b", W.s):
        times.append((m.start(), f"{m.group(3)}-{MONTHS[m.group(2)][0]:02d}-{int(m.group(1)):02d}")); W.eat(m.start(), m.end())
    for m in re.finditer(rf"\b({mon})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(20\d\d)\b", W.s):
        times.append((m.start(), f"{m.group(3)}-{MONTHS[m.group(1)][0]:02d}-{int(m.group(2)):02d}")); W.eat(m.start(), m.end())
    for m in re.finditer(rf"(?:\b(?:de|del|of|in|en|em|durante|during)\s+)?\b({mon})\b(?:\s*(?:de|del|of|,|em)?\s*(20\d\d))?", W.s):
        name = m.group(1)
        prev = W.orig[:m.start(1)].rstrip().split(" ")[-2:]
        if W.orig[m.start(1)].isupper() and len(prev) == 2 and prev[0][:1].isupper() and prev[1].lower() in ("de", "of", "do"):
            continue   # place name such as 'Rio de Janeiro', not a month
        if name == "may" and not re.search(r"\b(in|of|during|for)\s+may\b|may\s+20\d\d", m.group(0) + W.s[m.end():m.end() + 6]):
            continue
        num, code = MONTHS[name]
        if m.group(2):
            times.append((m.start(), f"{m.group(2)}-{num:02d}"))
        else:
            times.append((m.start(), code)); f.conditions.append("AMBIGUOUS_YEAR")
        W.eat(m.start(), m.end())
    for m in re.finditer(r"\b(?:en|in|de|del|em|do|para|for|of|durante|during|from|desde|since|until|by|no|na)\s+(?:el\s+|o\s+|the\s+)?(?:ano\s+|year\s+)?((?:19|20)\d\d)\b|\b(?:ano|year)\s+((?:19|20)\d\d)\b", W.s):
        times.append((m.start(), m.group(1) or m.group(2))); W.eat(m.start(), m.end())
    if any(re.fullmatch(r"(?:19|20)\d\d", v) for _, v in times):
        for m in re.finditer(r"\b(?:y|and|e|con|with|vs|contra|against)\s+((?:19|20)\d\d)\b", W.s):
            times.append((m.start(), m.group(1))); W.eat(m.start(), m.end())
    for code, rx in REL_RX:
        for m in re.finditer(rx, W.s):
            times.append((m.start(), code)); W.eat(m.start(), m.end())
    if times:
        f.time = ",".join(v for _, v in sorted(times))

    # 5. conditions (incl. confidence inside an if-clause) and confidence field
    spans = []
    for m in COND_MARK.finditer(W.s):
        end = re.compile(r",(?!\d)|\.(?!\d)|;| entonces\b| then\b").search(W.s, m.end())
        spans.append((m.start(), end.start() if end else len(W.s)))

    def in_span(i):
        return any(a <= i < b for a, b in spans)

    def cmp_of(mid):
        for op, rx in CMP_RX:
            if re.search(rx, mid):
                return op
        return "="

    for m in list(re.finditer(r"(\d+(?:[.,]\d+)?)\s*%\s*(?:de\s+|of\s+)?(?:confianza|confidence|confianca)\b", W.s)):
        val = norm_decimal(f"{float(_num(m.group(1))) / 100:.2f}")
        if in_span(m.start()):
            f.conditions.append(f"H={val}")
        else:
            f.confidence = f"={val}"
        W.eat(m.start(), m.end())
    for m in list(re.finditer(r"(?P<mid>[^0-9;.]{0,30}?)(?P<num>\d*\.\d+|\d+)\s+(?:de\s+)?(?:confidence|confianza|confianca)\b", W.s)):
        if re.search(r"%", m.group(0)):
            continue
        op = cmp_of(m.group("mid"))
        val = norm_decimal(_num(m.group("num")))
        if in_span(m.start()):
            f.conditions.append(f"H{op}{val}")
        else:
            f.confidence = f"{op}{val}"
        W.eat(m.start("num"), m.end())
    for m in list(CONF_RX.finditer(W.s)):
        op = cmp_of(m.group("mid"))
        n = _num(m.group("num"))
        if m.group("pct"):
            n = f"{float(n) / 100:.2f}"
        val = norm_decimal(n)
        if in_span(m.start()):
            f.conditions.append(f"H{op}{val}")
        else:
            f.confidence = f"{op}{val}"
        W.eat(m.start(), m.end())
    for m in list(EXIST_RX.finditer(W.s)):
        word = m.group("n1") or m.group("n2")
        canon = next((k for k, rx in DATA_RX + ENTITY_RX if re.fullmatch(rx.replace(r"\b", ""), word)), None)
        f.conditions.append(f"{canon or word.upper()}_EXISTS")
        W.eat(m.start(), m.end())

    # 6. approximations and limits
    for m in list(re.finditer(r"\b(aproximadamente|approximately|approx\.?|about|around|cerca de|alrededor de|roughly)\s+(\d[\d.,]*)", W.s)):
        f.constraints.append(f"APPROX={_num(m.group(2).rstrip('.,'))}"); W.eat(m.start(), m.end())
    for m in list(re.finditer(r"\b(maximo(?: de)?|max|maximum(?: of)?|a maximum of|a maximo de|at most|up to|hasta|ate|no maximo|limit(?:e|ed)?\s*(?:de|to|of)?|limita\w*\s+a|top|no more than|no mas de|como maximo|at the most)\s+(\d[\d.,]*)(?:\s+(?:de\s+)?(?:results?|resultados?|rows?|records?|registros?|filas?|items?))?", W.s)):
        f.constraints.append(f"LIMIT={_num(m.group(2).rstrip('.,'))}"); W.eat(m.start(), m.end())

    nouns = "|".join(rx.replace(r"\b", "") for _, rx in DATA_RX + ENTITY_RX)
    for m in list(re.finditer(rf"\b(\d[\d.,]*\d|\d)\s+(?:de\s+)?(?={'(?:' + nouns + ')'}\b)", W.s)):
        f.constraints.append(f"COUNT={_num(m.group(1))}"); W.eat(m.start(), m.end(1))

    # 7. location (capitalized chain; accepted only if a known place/country is inside)
    for m in re.finditer(r"(?i:\b(?:en|in|em|de|from|desde|para|for|at)\s+(?:(?-i:the|el|la|los)\s+)?)((?:[A-ZÁÉÍÓÚÑ][\w'áéíóúñ.-]*)(?:\s+(?:(?:de|del|la|of)\s+)?[A-ZÁÉÍÓÚÑ][\w'áéíóúñ.-]*)*(?:\s*,\s*[A-ZÁÉÍÓÚÑ][\w'áéíóúñ.-]*(?:\s+[A-ZÁÉÍÓÚÑ][\w'áéíóúñ.-]*)*)*)", W.orig):
        parts = [p.strip().rstrip(".") for p in m.group(1).split(",")]
        keys = [_strip(p).upper().replace(" ", "_") for p in parts]
        if any(k.lower() in NON_PLACE for k in keys):
            continue
        known = [(k.replace("_", " ") in COUNTRIES) or (k in PLACES) for k in keys]
        if not any(known):
            continue
        f.location = [COUNTRIES.get(k.replace("_", " "), k) for k in keys]
        W.eat(m.start(), m.end())
        break

    # 8. priority
    if re.search(r"\b(urgente|urgent|urgentemente|asap|lo antes posible|as soon as possible)\b", W.s):
        f.priority = "URGENT"
    elif re.search(r"\b(alta prioridad|prioridad alta|high priority|high-priority|prioridade alta|con prioridad alta|priority high|prioridad es alta|priority is high|prioridade e alta|prioridade é alta)\b", W.s):
        f.priority = "HIGH"
    elif re.search(r"\b(baja prioridad|prioridad baja|low priority|prioridade baixa)\b", W.s):
        f.priority = "LOW"

    # 9. actions (+ negation / modality)
    for act, rx in ACTION_RX:
        for m in re.finditer(rx, W.s):
            before = W.s[max(0, m.start() - 30):m.start()]
            neg = bool(NEG_BEFORE.search(before))
            modal = bool(MODAL_BEFORE.search(before))
            pos["A"].append((m.start(), act, neg, modal))
            W.eat(m.start(), m.end())
    pos["A"].sort()
    for _, act, neg, modal in pos["A"]:
        if act not in f.actions:
            f.actions.append(act)
        if neg:
            f.negations.append(f"NO_{act}"); f.constraints.append(f"FORBID_{act}")
        elif modal and act in RISKY:
            f.conditions.append("AMBIGUOUS_MODALITY")
            warns.append(f"modalidad ambigua (permiso vs. solicitud) para {act}")

    # 10. data / entities (by first appearance)
    for target, table in (("D", DATA_RX), ("E", ENTITY_RX)):
        found = []
        for canon, rx in table:
            for m in re.finditer(rx, W.s):
                found.append((m.start(), canon)); W.eat(m.start(), m.end())
        vals = []
        for _, c in sorted(found):
            if c not in vals: vals.append(c)
        setattr(f, "data" if target == "D" else "entities", vals)

    # 11. leftover if-clauses are kept as quoted literals, never dropped or invented
    for a, b in spans:
        rest = W.s[a:b]
        words = [w for w in re.findall(r"[a-z]{2,}", rest) if w not in STOP and not COND_MARK.fullmatch(w)]
        if words:
            f.conditions.append(W.orig[a:b].strip())
            warns.append(f"condición no normalizada, conservada literal: {W.orig[a:b].strip()!r}")

    # 12. intent and goal
    from aixl.legacy02.protocol.atoms import derive_intent
    f.intent = derive_intent(f.actions, [n[3:] for n in f.negations])
    if f.intent == "UNKNOWN":
        warns.append("sin acción reconocida: intent=UNKNOWN")
    from aixl.legacy02.protocol.atoms import derive_goal
    f.goal = derive_goal(f.actions, f.entities, [n[3:] for n in f.negations])

    for lit in literals:
        f.data.append(f'{lit}')
    from aixl.legacy02.core.normalizer import normalize
    n = normalize(f)
    n.lang, n.source, n.raw = f.lang, f.source, f.raw
    return n, warns
