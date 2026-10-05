"""AIXL 0.4 deterministic atom extractor (ES/EN/PT, controlled domain) -> AtomGraph.
Pipeline (master prompt §25): tokenize -> language -> condition split -> step split -> modality/action -> NP (entity, property, quantifier,
quantity, time, format, recipient, exception) -> reference resolution -> validation. Every stage that cannot decide leaves an explicit marker
(`x:` concept, status=ambiguous, REFERENCE) instead of guessing (§51). Concepts come from aixl.atoms.registry; function words from
aixl.semantic.lexicon (shared closed-class lists, not duplicated)."""
import re
import unicodedata
from aixl.atoms import registry as R
from aixl.atoms.schema import Atom, AtomGraph
from aixl.semantic import lexicon as L


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


_TOK = re.compile(r"[A-Za-zÀ-ÿ0-9'’\-]+|[,;.:]")
STOP = ({a for v in L.ARTICLES.values() for a in v} | {"de", "del", "of", "to", "a", "al", "ao", "en", "in", "on", "as", "como", "com", "con", "with", "for", "para", "por", "by",
        "from", "that", "que", "which", "ones", "those", "these", "this", "ese", "esa", "one", "um", "uma", "no", "na", "do", "da", "dos", "das", "pelo", "pela", "se", "ya",
        "o", "e", "y", "and", "or", "ou", "u", "you", "tu", "voce", "usted", "your", "su", "sus", "seu", "sua", "its", "their", "el", "ella", "le", "les", "mismo", "same", "also", "tambien", "algo", "something"}
        | {w for s in L.COPULA.values() for w in s} | set(L.FILLER_WORDS))
PREP_RECIP = {"a", "al", "to", "para", "for", "ao", "aos", "à"}
PREP_IN = {"en", "in", "em", "como", "as", "with", "con", "com", "of", "de"}
CLITIC_ENDS = ("lo", "la", "los", "las", "le", "les", "-o", "-a", "-os", "-as")
SEQ_WORDS = {"luego", "despues", "entonces", "then", "depois", "entao", "afterwards"}
FIRST_WORDS = {"primero", "first", "primeiro", "primeira"}
BUT = {"pero", "but", "mas", "porem"}
NEG1 = {"no", "nao", "not", "never", "nunca", "jamas", "nem"}
OTHER = {"otro", "otra", "otros", "otras", "outro", "outra", "outros", "outras", "another", "other"}
PRON_OBJ = {"it", "them", "lo", "la", "los", "las"}
PERSON_NEG = {"nadie": "person", "nobody": "person", "ninguem": "person", "anyone": "person", "anybody": "person"}
THING_NEG = {"nada": "thing", "nothing": "thing", "tudo": "thing"}
RECIPIENT_VERBS = {"ACT.NOTIFY", "ACT.PAY", "ACT.REFUND"}
OUTPUT_UNITS = {"word", "character", "page", "sentence", "line", "paragraph", "mb", "item"}
TIME_UNITS = {"hour": "h", "minute": "min", "day": "d", "week": "w", "month": "mo"}
DAYS = {k: v for k, v in {**L.DAYS, **L.DAYS_PT_FEIRA}.items()}
RELDAYS = {k: v for k, v in L.RELDAYS.items() if v in ("today", "tomorrow", "yesterday")}
NUMW = L.NUM_WORDS
QUANTIFIERS = dict(L.QUANTIFIERS)
QTY_PHRASES = sorted([(t, {"greater_than": "more_than"}.get(m, m)) for t, m in L.QTY_PHRASES], key=lambda x: -len(x[0]))
TIME_REL = sorted([x for x in L.TIME_REL if x[1] in ("before", "after", "until", "since", "within")], key=lambda x: -len(x[0]))
EXC_WORDS = sorted(L.EXCEPT_WORDS, key=lambda x: -len(x[0]))
COND_NEC = sorted(L.COND_NEC, key=lambda x: -len(x))
COND_UNLESS = sorted(L.COND_UNLESS, key=lambda x: -len(x))
COND_IF = {("si",), ("if",), ("se",), ("when",), ("cuando",), ("quando",), ("whenever",)}
LIT = list(L.LITOTES)
NOT_REQ = sorted(L.NOT_REQUIRED, key=lambda x: -len(x))
MAY_W = {"puedes", "puede", "pueden", "pode", "podem", "may", "can"}
ADV_W = {"should", "deberias", "deberia", "deve", "recomienda", "recomendable", "convem"}
PROHIB = L.PROHIBITED | {"forbidden"}
AVOID = set(L.AVOID)


def _stems():
    st = []
    for c in R.CONCEPTS:
        if c.get("learned"): continue
        if c["type"] == "ACTION":
            for lang in c["lex"].values():
                for s in lang: st.append((fold(s), c["id"]))
    return sorted(set(st), key=lambda x: -len(x[0]))


def _lexicon(kind):
    out = {}
    for c in R.CONCEPTS:
        if c.get("learned"): continue
        if c["type"] == kind:
            for lang in c["lex"].values():
                for s in lang: out[fold(s)] = c["id"]
    return out


ACTION_STEMS = _stems()
ENTITY_LEX, PROP_LEX, FMT_LEX = _lexicon("ENTITY"), _lexicon("PROPERTY"), _lexicon("FORMAT")
UNIT_LEX = {fold(s): u for u, ss in R.UNITS.items() for s in ss}


class T:
    __slots__ = ("raw", "f", "i", "clitic")

    def __init__(self, raw, i, clitic=False):
        self.raw, self.f, self.i, self.clitic = raw, fold(raw).replace("’", "'"), i, clitic

    def __repr__(self): return self.f


def tokenize(text):
    out = []
    for m in _TOK.finditer(text):
        w = m.group(0)
        if "-" in w and fold(w.rsplit("-", 1)[1]) in ("o", "a", "os", "as", "lo", "la", "los", "las", "se") and len(w.rsplit("-", 1)[0]) > 2:
            h, tl = w.rsplit("-", 1)
            out.append(T(h, len(out))); out.append(T(tl, len(out), clitic=True))
        else:
            out.append(T(w, len(out)))
    return out


_LANG_LEX = {k: {} for k in ("es", "en", "pt")}
for _c in R.CONCEPTS:
    if _c.get("learned"): continue
    for _l, _forms in _c["lex"].items():
        if _c["type"] in ("ENTITY", "PROPERTY"):
            for _f in _forms: _LANG_LEX[_l][fold(_f)] = _c["id"]
_SHARED = {k for k in _LANG_LEX["es"] if k in _LANG_LEX["en"] or k in _LANG_LEX["pt"]} | {k for k in _LANG_LEX["en"] if k in _LANG_LEX["pt"]}


def detect_lang(toks):
    sc = {k: sum(1 for t in toks if t.f in v) for k, v in L.LANG_HINTS.items()}
    for t in toks:                                          # language-specific registry forms (plural-tolerant)
        for k, lex in _LANG_LEX.items():
            if any(g.startswith(m) and m not in _SHARED and len(m) >= 4 and len(g) - len(m) <= 4 for g in _plural_variants(t.f) for m in lex): sc[k] += 1
    if any(c in "ñ" for t in toks for c in t.raw.lower()): sc["es"] += 2
    if any(c in "ãõç" for t in toks for c in t.raw.lower()): sc["pt"] += 2
    return max(sc, key=sc.get) if max(sc.values()) else "en"


def _near(f, lex, maxdiff=3):
    """longest lexeme that is a prefix of f within maxdiff characters (plural/gender endings)."""
    best = None
    for k, v in lex.items():
        if f.startswith(k) and len(f) - len(k) <= (maxdiff + 2 if len(k) >= 5 else maxdiff) and len(k) >= 3 and (best is None or len(k) > len(best[0])):
            best = (k, v)
    return best[1] if best else None


def _plural_variants(f):
    v = [f]
    if f.endswith("ns"): v.append(f[:-2] + "m")
    if f.endswith("oes"): v.append(f[:-3] + "ao")
    if f.endswith("ies"): v.append(f[:-3] + "y")
    return v


def _entity(f):
    for g in _plural_variants(f):
        r = ENTITY_LEX.get(g) or _near(g, ENTITY_LEX)
        if r: return r
    return None


def _prop(f):
    return PROP_LEX.get(f) or _near(f, PROP_LEX, 4)


def _verb(f):
    if _entity(f) and f not in ("copia",):
        pass
    for s, cid in ACTION_STEMS:
        if f.startswith(s) and len(f) - len(s) <= 6 and not (f in ENTITY_LEX and f != "copia"):
            if len(s) <= 2 and len(f) - len(s) > 3: continue
            return cid
    return None


def _num(f):
    if re.fullmatch(r"\d+([.,]\d+)?", f): return float(f.replace(",", ".")) if re.search(r"[.,]", f) else int(f)
    return NUMW.get(f)


def _unit(f):
    if f in UNIT_LEX: return UNIT_LEX[f]
    for k, u in UNIT_LEX.items():
        if len(k) >= 3 and f.startswith(k) and len(f) - len(k) <= 2: return u
    return None


class Builder:
    def __init__(self):
        self.atoms, self.rels, self.n = [], [], 0
        self.unplaced = []

    def add(self, type_, **kw):
        self.n += 1
        a = Atom(id=kw.pop("id", f"a{self.n}"), type=type_, **kw)
        self.atoms.append(a)
        return a

    def rel(self, s, r, d):
        if s and d and (s.id, r, d.id) not in self.rels: self.rels.append((s.id, r, d.id))


class Step:
    def __init__(self, toks):
        self.toks = toks
        self.action = None
        self.targets = []      # entity/ref atoms that are TARGETS
        self.pending_order = None


def _is_verb_at(toks, i):
    if i >= len(toks): return False
    t = toks[i]
    if t.f in STOP and t.f not in ("us",): return False
    return _verb(t.f) is not None or (t.f in NEG1 and i + 1 < len(toks) and _verb(toks[i + 1].f))


def _match_seq(toks, i, table):
    for tup in table:
        n = len(tup)
        if tuple(t.f for t in toks[i:i + n]) == tup: return tup
    return None


def extract(text: str, lang: str | None = None) -> AtomGraph:
    toks = [t for t in tokenize(text) if t.f not in ("please", "porfa", "favor")]
    toks = [t for t in toks if not (t.f in (".",) )]
    lang = lang or detect_lang(toks)
    b = Builder()
    g_conds = []   # (container atom, body tokens, kind)
    toks, cond = _split_condition(toks)
    steps = _split_steps(toks)
    for st in steps: _parse_step(st, b, lang)
    _link_sequence(steps, b)
    if cond: _attach_condition(cond, steps, b)
    _resolve_refs(steps, b)
    for a in b.atoms:
        if a.concept and a.concept.startswith("x:"): b.unplaced.append("term:" + a.concept[2:])
    g = AtomGraph(atoms=b.atoms, relations=b.rels, text=text, lang=lang, unrepresented=sorted(set(b.unplaced)))
    if not b.atoms: g.unrepresented = sorted(set(b.unplaced) | {"no_atoms"})
    return g


# ---------------------------------------------------------------- conditions
def _split_condition(toks):
    # (conditions with an action inside the body are not representable in v0.2: the body parser flags them via cond_body:*)
    fs = [t.f for t in toks]
    # leading: if X, MAIN
    if toks and (toks[0].f,) in COND_IF:
        k = next((j for j, t in enumerate(toks) if t.f == ","), None)
        if k is None:
            k = next((j for j in range(2, len(toks)) if _is_verb_at(toks, j)), None)
        if k is not None:
            return toks[k + 1:], dict(kind="if", neg=False, body=toks[1:k], lead=True)
    for i in range(1, len(toks)):
        tup = _match_seq(toks, i, COND_NEC)
        if tup: return _trim(toks[:i]), dict(kind="only_if", neg=False, body=toks[i + len(tup):], lead=False)
        tup = _match_seq(toks, i, COND_UNLESS)
        if tup: return _trim(toks[:i]), dict(kind="if", neg=True, body=toks[i + len(tup):], lead=False)
    for i in range(1, len(toks)):
        if (toks[i].f,) in COND_IF and any(_is_verb_at(toks, j) for j in range(0, i)):
            prev = toks[i - 1].f
            if prev.startswith(("comprueb", "verific", "check", "confirm")) or toks[i].f == "whether":
                return _trim(toks[:i]), dict(kind="whether", neg=False, body=toks[i + 1:], lead=False)
            return _trim(toks[:i]), dict(kind="if", neg=False, body=toks[i + 1:], lead=False)
    return toks, None


def _trim(toks):
    while toks and toks[-1].f in (",", ";"): toks = toks[:-1]
    return toks


# ---------------------------------------------------------------- steps
def _split_steps(toks):
    """Cut the token list into one segment per action. Returns list of Step with .pre (order word) set."""
    if not toks: return []
    cuts = [0]
    i = 0
    n = len(toks)
    while i < n:
        t = toks[i]
        brk = False
        if i > 0 and t.f in (",", ";"): brk = True
        elif i > 0 and t.f in {"y", "and", "e", "but", "pero", "mas"} | BUT:
            brk = True
        elif i > 0 and t.f in SEQ_WORDS: brk = True
        if brk:
            j = i + 1
            while j < n and (toks[j].f in (SEQ_WORDS | FIRST_WORDS | {",", "y", "and", "e", "un", "una"})):
                j += 1
            if j < n and (_is_verb_at(toks, j) or _starts_modal(toks, j) or (toks[j].f in ("lo", "la", "los", "las") and _is_verb_at(toks, j + 1))):
                cuts.append(i)
                i = j
                continue
        i += 1
    segs = []
    for k, c in enumerate(cuts):
        e = cuts[k + 1] if k + 1 < len(cuts) else n
        segs.append(toks[c:e])
    out = []
    for s in segs:
        st = Step(s)
        # order words at the head of the segment
        lead = []
        while s and (s[0].f in SEQ_WORDS | FIRST_WORDS | {",", "y", "and", "e", "but", "pero", "mas"}):
            lead.append(s[0].f); s = s[1:]
        st.toks = s
        st.pending_order = "seq" if any(w in SEQ_WORDS for w in lead) else ("first" if any(w in FIRST_WORDS for w in lead) else None)
        out.append(st)
    out = [s for s in out if s.toks]
    # "before V1 ..., V2" / "after V1 ..., V2": a prefixed temporal clause (V1) is its own step
    fixed = []
    for st in out:
        fs = [t.f for t in st.toks]
        for rel_tokens, kind in ((("antes", "de"), "before"), (("before",), "before"), (("despues", "de"), "after"), (("after",), "after"), (("depois", "de"), "after"), (("antes", "do"), "before")):
            k = len(rel_tokens)
            if tuple(fs[:k]) == rel_tokens and len(st.toks) > k and _verb(st.toks[k].f) and (kind == "before" or _verb(st.toks[k].f)):
                st.toks = st.toks[k:]
                st.temporal_clause = kind
        fixed.append(st)
    return fixed


def _starts_modal(toks, j):
    f = toks[j].f
    return f in NEG1 or f in AVOID or f in MAY_W or f in ADV_W or f in ("you", "voce", "tu") or f in PROHIB or (f == "e" and j + 1 < len(toks) and toks[j + 1].f in PROHIB)


# ---------------------------------------------------------------- step parsing
def _parse_step(st: Step, b: Builder, lang: str):
    toks = st.toks
    i = 0
    modality = "DO"
    ref_pre = None
    fs = [t.f for t in toks]
    # modality prefix
    while i < len(toks):
        f = toks[i].f
        if tuple(fs[i:i + 3]) in LIT or tuple(fs[i:i + 4]) in LIT:
            i += 3 if tuple(fs[i:i + 3]) in LIT else 4; modality = "DO"; continue
        nr = next((x for x in NOT_REQ if tuple(fs[i:i + len(x)]) == x), None)
        if nr: i += len(nr); modality = "NOT_REQUIRED"; continue
        if f == "do" and i + 1 < len(toks) and fs[i + 1] in ("not", "n't"): i += 2; modality = "DONT"; continue
        if f in ("don't", "dont", "do not"): i += 1; modality = "DONT"; continue
        if f in NEG1: i += 1; modality = "DONT"; continue
        if f in AVOID: i += 1; modality = "DISCOURAGE"; continue
        if f in MAY_W: i += 1; modality = "MAY"; continue
        if f in ADV_W: i += 1; modality = "ADVISE"; continue
        if f in PROHIB or (f == "e" and i + 1 < len(toks) and fs[i + 1] in PROHIB): i += 2 if f == "e" else 1; modality = "DONT"; continue
        if f in ("is", "es", "are", "you", "voce", "tu", "usted", "se") and i + 1 < len(toks) and (fs[i + 1] in PROHIB | MAY_W | ADV_W | NEG1 or _verb(fs[i + 1])): i += 1; continue
        if f in ("lo", "la", "los", "las") and i + 1 < len(toks) and _verb(fs[i + 1]):
            ref_pre = toks[i]; i += 1; continue
        break
    if i >= len(toks):
        b.unplaced.append("dangling_modality")
        return
    # action
    t = toks[i]
    cid = _verb(t.f)
    clit = False
    if cid is None:
        if t.f in STOP or _num(t.f) is not None: cid = None
        else: cid = "x:" + t.f
    if cid is None:
        b.unplaced += ["no_verb:" + " ".join(x.f for x in toks[i:] if x.f not in STOP)[:40]]
        return
    # clitic attached to verb: envialo / fírmalo / cancelalo (accent or hyphen evidence)
    clit_ref = ref_pre
    raw = t.raw
    if not t.clitic and re.search(r"[áéíóú]", raw.lower()) and fs[i].endswith(CLITIC_ENDS[:4]):
        clit_ref = t
    nxt = toks[i + 1] if i + 1 < len(toks) else None
    if nxt is not None and nxt.clitic: clit_ref = nxt; i += 1
    i += 1
    act = b.add("ACTION", concept=cid, modality=modality, span=t.raw)
    st.action = act
    st.after = []
    _parse_np(toks, i, st, b, clit_ref, lang)


def _qty_at(toks, i):
    """-> (qty value dict | None, next_i, kind) ; kind: 'unit'|'count'|'bare'."""
    n = len(toks)
    mode = "exact"
    j = i
    for tup, m in QTY_PHRASES:
        if tuple(t.f for t in toks[j:j + len(tup)]) == tup:
            nx = j + len(tup)
            if nx < n and (_num(toks[nx].f) is not None or toks[nx].f in ("un", "una", "uma", "a", "one")):
                mode = m; j = nx; break
    else:
        if j >= n: return None
    f = toks[j].f
    num = _num(f)
    if num is None and f in ("un", "una", "uma", "a", "an", "one") and j + 1 < n and _unit(toks[j + 1].f) and mode == "exact" and j > i - 1: num = 1
    if num is None: return None
    k = j + 1
    if k < n and toks[k].f in ("de", "of") and k + 1 < n: pass
    unit = None
    if k < n:
        u = _unit(toks[k].f)
        if u and not (_entity(toks[k].f) and u == "item"):
            unit = u; k += 1
            if k < n and toks[k].f in ("points", "puntos", "pontos"): k += 1
        elif _entity(toks[k].f): return dict(mode=mode, n=num, unit="item"), k, "count"
    if unit is None: return None
    return dict(mode=mode, n=num, unit=unit), k, "unit"


def _time_at(toks, i):
    """-> (value, next_i, ambiguous_candidates) or None."""
    n = len(toks)
    for tup, rel in TIME_REL:
        if tuple(t.f for t in toks[i:i + len(tup)]) == tup:
            j = i + len(tup)
            while j < n and toks[j].f in ("el", "la", "las", "los", "o", "a", "the", "las", "de"): j += 1
            cands = []
            ref = _time_ref(toks, j)
            if ref is None: return None
            val, k = ref
            if rel == "before" and tup[0] == "antes": cands = ["until"]
            if rel == "within" and not str(val)[:1].isdigit(): return None
            return dict(rel=rel, ref=val), k, cands
    # bare weekday / relative day
    j = i
    pre = None
    if toks[j].f in ("every", "cada", "todos", "todas", "todo") :
        pre = "every"; j += 1
        while j < n and toks[j].f in ("los", "las", "el", "la", "os", "as"): j += 1
    elif toks[j].f in ("el", "on", "no", "na", "los", "en"):
        k = j + 1
        if k < n and (toks[k].f in DAYS):
            pre = "at"; j = k
    ref = _time_ref(toks, j)
    if ref and (pre or toks[j].f in RELDAYS or toks[j].f in DAYS):
        val, k = ref
        return dict(rel=pre or "at", ref=val), k, []
    return None


def _time_ref(toks, j):
    n = len(toks)
    if j >= n: return None
    f = toks[j].f
    if f in DAYS: return DAYS[f], j + 1
    if f in RELDAYS: return RELDAYS[f], j + 1
    num = _num(f)
    if num is not None and j + 1 < n:
        u = _unit(toks[j + 1].f)
        if u in TIME_UNITS: return f"{num}{TIME_UNITS[u]}", j + 2
    return None


def recipient_seen(b, act):
    return any(r[0] == act.id and r[1] == "RECIPIENT" for r in b.rels)


def _parse_np(toks, i, st, b, clit_ref, lang="en"):
    n = len(toks)
    act = st.action
    quant = None
    cur_ent = None
    ents = []
    pending_props = []
    pending_other = False
    last_unknown = []
    exc_mode = None          # 'except' | 'only'
    recip_next = False
    in_prep = None
    restrict_next = False
    st.after = []
    if clit_ref is not None:
        r = b.add("REFERENCE", value="prev", span=clit_ref.raw)
        b.rel(act, "TARGETS", r); st.targets.append(r); st.has_ref = r
    def flush_unknown():
        nonlocal last_unknown, cur_ent
        if last_unknown:
            lem = "_".join(last_unknown)
            if len(lem) > 3 and lem.endswith("s") and not lem.endswith("ss"): lem = lem[:-1]
            e = b.add("ENTITY", concept="x:" + lem)
            cur_ent = _place_entity(e, act, b, st, recip_next, quant, pending_props, ents)
            last_unknown = []
    def hook(e):
        return e
    while i < n:
        t = toks[i]; f = t.f
        # exception
        tup = _match_seq(toks, i, EXC_WORDS)
        if tup and ents:
            flush_unknown(); exc_mode = "except"; i += len(tup); excl_start = True
            base = ents[-1] if ents else None
            # parse the excluded NP: properties and optionally a noun
            props, noun = [], None
            while i < n and toks[i].f not in (",", ";"):
                g = toks[i].f
                if _prop(g): props.append(_prop(g))
                elif _entity(g): noun = _entity(g)
                i += 1
            if base is not None:
                e2 = b.add("ENTITY", concept=noun or base.concept)
                for p in props: b.rel(e2, "HAS_PROPERTY", b.add("PROPERTY", concept=p))
                b.rel(base, "EXCLUDES", e2)
            continue
        if f in ("solo", "only", "solamente", "apenas", "somente", "just", "unicamente"):
            restrict_next = True; i += 1; continue
        # time
        tm = _time_at(toks, i)
        if tm and not (toks[i].f in ("en", "in", "em") and tm[0]["rel"] == "at"):
            flush_unknown()
            val, k, cands = tm
            ta = b.add("TIME", value=val, status="ambiguous" if cands else "explicit", candidates=cands, span=" ".join(x.raw for x in toks[i:k]))
            b.rel(act, "OCCURS_AT", ta); i = k; continue
        # preposition + quantity/time/format
        if f in ("en", "in", "em", "within", "con", "with", "de", "of", "mantenha", "no", "up", "as", "como") or _match_seq(toks, i, [x[0] for x in QTY_PHRASES]):
            j = i
            if f in ("en", "in", "em", "con", "with", "de", "of", "as", "como") : j = i + 1
            q = _qty_at(toks, j)
            if q is not None:
                flush_unknown()
                val, k, kind = q
                if val["unit"] in TIME_UNITS and (f in ("en", "in", "em") or val["mode"] in ("at_most", "less_than")):
                    ta = b.add("TIME", value=dict(rel="within", ref=f"{val['n']}{TIME_UNITS[val['unit']]}"), span=" ".join(x.raw for x in toks[i:k]))
                    b.rel(act, "OCCURS_AT", ta)
                else:
                    qa = b.add("QUANTITY", value=val, span=" ".join(x.raw for x in toks[i:k]))
                    if act.concept == "ACT.KEEP":
                        if ents: b.rel(ents[-1], "CONSTRAINED_BY", qa)
                        else: st.pending_count = qa
                    elif kind == "count" and ents:
                        b.rel(ents[-1] if _nextent(toks, k) is None else ents[-1], "CONSTRAINED_BY", qa)
                    elif kind == "count":
                        st.pending_count = qa
                    else:
                        b.rel(act, "CONSTRAINED_BY", qa)
                i = k; continue
            if f in ("en", "in", "em", "as", "como", "with") and j < n and toks[j].f in FMT_LEX:
                flush_unknown()
                b.rel(act, "OUTPUT_AS", b.add("FORMAT", concept=FMT_LEX[toks[j].f], span=toks[j].raw)); i = j + 1; continue
            if f in ("as", "como", "en", "in") and j < n and toks[j].f in ("a", "an", "un", "una", "uma") and j + 1 < n and toks[j + 1].f in FMT_LEX:
                flush_unknown()
                b.rel(act, "OUTPUT_AS", b.add("FORMAT", concept=FMT_LEX[toks[j + 1].f])); i = j + 2; continue
        if f in FMT_LEX:
            flush_unknown(); b.rel(act, "OUTPUT_AS", b.add("FORMAT", concept=FMT_LEX[f])); i += 1; continue
        if f in PREP_RECIP:
            flush_unknown()
            if f in ("a", "al", "à") and not (st.targets or ents or recipient_seen(b, act)):
                if f == "a" and lang == "en": i += 1; continue
                i += 1; continue                       # direct-object marker / article: no recipient role
            recip_next = True; cur_ent = None; i += 1; continue
        if f in ("de", "del", "of"):
            i += 1; continue
        # other
        if f in OTHER:
            pending_other = True; i += 1; continue
        # pronoun object
        if f in PRON_OBJ and not _entity(f) and _is_pronoun(toks, i):
            flush_unknown()
            r = b.add("REFERENCE", value="prev", span=t.raw)
            _target(b, act, r, recip_next); st.targets.append(r); recip_next = False; i += 1; continue
        # quantity bare number before entity ("3 archivos")
        # quantifier / negative quantifiers
        if f in QUANTIFIERS and f not in PERSON_NEG and f not in THING_NEG:
            flush_unknown()
            quant = QUANTIFIERS[f]; i += 1; continue
        if f in PERSON_NEG or f in THING_NEG:
            flush_unknown(); cur_ent = None
            e = b.add("ENTITY", concept="ENT.PERSON" if f in PERSON_NEG else "x:thing")
            quant = "none"
            cur_ent = _place_entity(e, act, b, st, recip_next, quant, pending_props, ents); quant = None; recip_next = False; i += 1; continue
        if f in STOP or f in (",", ";", ":"):
            i += 1; continue
        # name
        if t.raw[:1].isupper() and not t.raw.isupper() and t.i > 0 and not _entity(f) and f not in DAYS and f not in RELDAYS and f not in FMT_LEX and not _prop(f):
            flush_unknown()
            name = [t.raw]; j = i + 1
            while j < n and toks[j].raw[:1].isupper() and not toks[j].raw.isupper() and toks[j].f not in DAYS:
                name.append(toks[j].raw); j += 1
            na = b.add("NAME", value=" ".join(name))
            _target(b, act, na, True if recip_next or True else False) if True else None
            recip_next = False; i = j; continue
        pe = _entity(f)
        if pe and not _prop(f):
            flush_unknown()
            e = b.add("ENTITY", concept=pe, span=t.raw)
            cur_ent = _place_entity(e, act, b, st, recip_next, quant, pending_props, ents, other=pending_other, restrict=restrict_next, qty=getattr(st, "pending_count", None))
            st.pending_count = None
            quant = None; recip_next = False; pending_other = False; restrict_next = False; i += 1; continue
        pp = _prop(f)
        if pp:
            flush_unknown()
            if cur_ent is not None and lang != "en":
                holder = restrict_ent(cur_ent, ents, b)
                b.rel(holder, "HAS_PROPERTY", b.add("PROPERTY", concept=pp, span=t.raw))
            else:
                pending_props.append(pp)
            i += 1; continue
        # unknown content word
        if cur_ent is not None and lang != "en":
            b.rel(restrict_ent(cur_ent, ents, b), "HAS_PROPERTY", b.add("PROPERTY", concept="x:" + f, span=t.raw))
        elif _is_prop_like(f, pending_props):
            pending_props.append("x:" + f)
        else:
            last_unknown.append(f)
        i += 1
    flush_unknown()
    if pending_props and ents:
        for p in pending_props: b.rel(restrict_ent(ents[-1], ents, b), "HAS_PROPERTY", b.add("PROPERTY", concept=p))
    if pending_other:
        r = b.add("REFERENCE", value="other"); b.rel(act, "TARGETS", r); st.targets.append(r); st.other_ref = r
    if pending_props and not ents:
        pass


def _is_pronoun(toks, i):
    f = toks[i].f
    if f in ("it", "them"): return True
    nxt = toks[i + 1].f if i + 1 < len(toks) else None
    if nxt is None or nxt in (",", ";", "y", "and", "e", "pero", "but") or nxt in PREP_RECIP or nxt in ("en", "in", "em", "con", "with"): return True
    return False


def _is_prop_like(f, pend):
    return False


def restrict_ent(cur, ents, b):
    """properties of 'only the X' belong to the restricted subset node."""
    return getattr(cur, "_prop_holder", cur)


def _nextent(toks, k):
    return None


def _target(b, act, node, recip):
    if recip: b.rel(act, "RECIPIENT", node)
    else: b.rel(act, "TARGETS", node)


def _place_entity(e, act, b, st, recip_next, quant, pending_props, ents, other=False, restrict=False, qty=None):
    holder = e
    if restrict:
        e2 = b.add("ENTITY", concept=e.concept)       # the restricted subset node carries the properties
        b.rel(e, "RESTRICTS_TO", e2)
        object.__setattr__(e, "_prop_holder", e2) if False else None
        e._prop_holder = e2
    for p in pending_props:
        b.rel(e._prop_holder if restrict else e, "HAS_PROPERTY", b.add("PROPERTY", concept=p))
    pending_props.clear()
    if quant:
        if quant == "none":
            q = b.add("QUANTIFIER", value="any"); act.modality = "DONT" if act.modality in (None, "DO") else act.modality
        else: q = b.add("QUANTIFIER", value=quant)
        b.rel(e, "QUANTIFIED_BY", q)
    if qty is not None: b.rel(e, "CONSTRAINED_BY", qty)
    ents.append(e)
    role_recip = recip_next or (act.concept in RECIPIENT_VERBS and not st.targets and not any(r[1] == "RECIPIENT" for r in b.rels if r[0] == act.id))
    if act.concept == "ACT.CALL": role_recip = False
    if other:
        r = b.add("REFERENCE", value="other"); b.rel(r, "REFERS_TO", e)
        _target(b, act, r, role_recip); st.targets.append(r)
    else:
        _target(b, act, e, role_recip)
        if not role_recip: st.targets.append(e)
    return e


# ---------------------------------------------------------------- sequence / conditions / references
def _link_sequence(steps, b):
    for k in range(1, len(steps)):
        a, c = steps[k - 1], steps[k]
        if a.action is None or c.action is None: continue
        tc = getattr(c, "temporal_clause", None)
        ta = getattr(a, "temporal_clause", None)
        if ta == "before": b.rel(c.action, "PRECEDES", a.action) if False else None
        if ta == "before" and k == 1:
            b.rel(c.action, "PRECEDES", a.action)          # 'before V1, V2': V2 happens first? -> see below
        elif ta == "after":
            b.rel(a.action, "PRECEDES", c.action)
        elif c.pending_order in ("seq",) or a.pending_order == "first":
            b.rel(a.action, "PRECEDES", c.action)


def _attach_condition(cond, steps, b):
    kind = cond["kind"]
    acts = [s for s in steps if s.action is not None]
    if not acts: return
    first = acts[-1] if kind == "whether" else acts[0]
    c = b.add("CONDITION", value=kind)
    body = cond["body"]
    sc = c.id
    main_ent = next((x for x in first.targets if x.type == "ENTITY"), None)
    others = [x for s in acts if s is not first for x in s.targets if x.type in ("ENTITY",)]
    # subject + properties
    subj = None; neg = False; props = []
    i = 0
    n = len(body)
    ref_subject = False
    while i < n:
        f = body[i].f
        if f in ("not", "no", "nao", "nunca", "never", "n't"): neg = True
        elif f in ("and", "y", "e"): neg = False
        elif _entity(f) and subj is None:
            subj = b.add("ENTITY", concept=_entity(f), scope=sc, span=body[i].raw)
        elif _prop(f):
            pol = "-" if (neg != cond["neg"]) else "+"
            props.append((_prop(f), pol))
        elif f in ("it", "ele", "ela") : ref_subject = True
        elif f in STOP or f in L.COPULA["es"] | L.COPULA["pt"] | L.COPULA["en"] or f in (",", "."): pass
        elif subj is None and not props and _verb(f) is None and not _num(f):
            props.append(("x:" + f, "-" if (neg != cond["neg"]) else "+"))
        else:
            b.unplaced.append("cond_body:" + f)
        i += 1
    if subj is None:
        if kind == "whether" and main_ent is None:
            subj = b.add("REFERENCE", value="prev", scope=sc)
            first.cond_ref_subject = subj
        elif main_ent is not None:
            subj = b.add("ENTITY", concept=main_ent.concept, scope=sc)
        else:
            subj = b.add("REFERENCE", value="prev", scope=sc)
    for p, pol in props:
        pa = b.add("PROPERTY", concept=p, polarity=pol, scope=sc)
        b.rel(subj, "HAS_PROPERTY", pa)
    if kind == "whether":
        b.rel(first.action, "TARGETS", c)
        first.whether = c
        for rr in list(b.rels):                       # the question replaces the verb's plain target
            pass
        b.rels[:] = [r for r in b.rels if not (r[0] == first.action.id and r[1] == "TARGETS" and r[2] != c.id)]
        first.targets = []
        if subj.type == "REFERENCE": subj.pending_whether = True
    else:
        for s in acts:
            b.rel(s.action, "CONDITIONED_BY", c)
        # a trailing condition governs the whole clause; apply to every step for a trailing/leading condition of a single-action text
        for s in steps[1:]:
            if s.action is not None and len([x for x in steps if x.action is not None]) > 1 and False:
                b.rel(s.action, "CONDITIONED_BY", c)
    first.cond_subject = subj
    first.cond_entity = subj if subj.type == "ENTITY" else None


def _resolve_refs(steps, b):
    ids = b.by_id() if hasattr(b, "by_id") else {a.id: a for a in b.atoms}
    # entities that can be antecedents, in textual order (condition-body entities included)
    ents = [a for a in b.atoms if a.type == "ENTITY" and a.scope is None]
    body_ents = [a for a in b.atoms if a.type == "ENTITY" and a.scope]
    def antecedent(ref, step_idx):
        # prefer an entity targeted in an earlier step; then one in a later step; then a condition-body entity
        for s in reversed(steps[:step_idx]):
            for x in s.targets:
                if x.type == "ENTITY": return x
                if x.type == "REFERENCE":
                    ant = next((r[2] for r in b.rels if r[0] == x.id and r[1] == "REFERS_TO"), None)
                    if ant: return ids[ant]
        for s in steps[step_idx + 1:]:
            for x in s.targets:
                if x.type == "ENTITY": return x
        for s in steps:
            ce = getattr(s, "cond_entity", None)
            if ce is not None and ce.type == "ENTITY": return ce
        return None
    for k, s in enumerate(steps):
        for x in list(s.targets) + [getattr(s, "other_ref", None), getattr(s, "cond_ref_subject", None)]:
            if x is None or x.type != "REFERENCE": continue
            if any(r[0] == x.id and r[1] == "REFERS_TO" for r in b.rels): continue
            ant = antecedent(x, k)
            if ant is not None: b.rel(x, "REFERS_TO", ant)
    for a in b.atoms:
        if a.type == "REFERENCE" and a.scope and not any(r[0] == a.id and r[1] == "REFERS_TO" for r in b.rels):
            for k, s in enumerate(steps):
                ant = antecedent(a, 0) if s is steps[0] else None
                if ant is not None: b.rel(a, "REFERS_TO", ant); break
