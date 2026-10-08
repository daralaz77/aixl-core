"""0.3-R parser for the controlled domain. Rule-based, ES/EN/PT, and FAIL-CLOSED by construction:
every content token that is not turned into a typed atom is kept as an ordered `item`, so nothing is silently dropped
(the failure mode of the 0.3 frame: no slot -> meaning disappears). Constructs the parser cannot represent raise flags."""
import re
import unicodedata
from aixl.core.normalizer import sanitize_input
from aixl.semantic import lexicon as L
from aixl.semantic.model import Atom, Step, SemanticObject

PUNCT = {",", ";", ":", ".", "!", "?", "(", ")", "¿", "¡"}
_TOKEN_RX = re.compile(r"T\d{4}|ORD\d+|[A-Za-zÀ-ÿñÑ]+(?:[-'][A-Za-zÀ-ÿñÑ]+)*|\d+(?:[.,]\d+)*|[,;:.!?¿¡()]")
CONTRACTIONS = [(r"\bcan['’]?t\b", "can not"), (r"\bcannot\b", "can not"), (r"\bwon['’]t\b", "will not"), (r"\bdon['’]t\b", "do not"), (r"\bdoesn['’]t\b", "does not"),
                (r"\bdidn['’]t\b", "did not"), (r"\bisn['’]t\b", "is not"), (r"\baren['’]t\b", "are not"), (r"\bshouldn['’]t\b", "should not"), (r"\bmustn['’]t\b", "must not"),
                (r"\bwouldn['’]t\b", "would not"), (r"\bhasn['’]t\b", "has not"), (r"\bhaven['’]t\b", "have not"), (r"\bjohn['’]s\b", "john 's")]


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


class Tok:
    __slots__ = ("raw", "f", "initial")

    def __init__(self, raw, initial):
        self.raw, self.f, self.initial = raw, fold(raw), initial

    def __repr__(self):
        return self.f


def _clock_to_token(m):
    h = int(m.group(1)); mi = int(m.group(2) or 0); ap = (m.group(3) or "").replace(".", "").lower()
    if ap == "pm" and h < 12: h += 12
    if ap == "am" and h == 12: h = 0
    return f" T{h:02d}{mi:02d} "


def tokenize(text: str) -> list:
    s = text
    for rx, rep in CONTRACTIONS:
        s = re.sub(rx, rep, s, flags=re.I)
    s = re.sub(r"[$]\s?(\d[\d.,]*)", r"\1 usd", s)
    s = re.sub(r"€\s?(\d[\d.,]*)", r"\1 eur", s)
    s = re.sub(r"(\d+)\s?[ºª°]", r" ORD\1 ", s)
    s = re.sub(r"\b(\d{1,2})(?::(\d\d))?\s*(a\.?\s?m\.?|p\.?\s?m\.?)(?![a-z])", lambda m: _clock_to_token(re.match(r"(\d+)(?::(\d+))?\s*(.*)", m.group(0).replace(" ", ""))), s, flags=re.I)
    s = re.sub(r"\b(\d{1,2}):(\d\d)\b", lambda m: f" T{int(m.group(1)):02d}{m.group(2)} ", s)
    s = re.sub(r"\b(?:a\s+las\s+|às\s+|as\s+|a\s+la\s+)?(\d{1,2})\s?(?:h|hs|hrs)\b(?!\w)", lambda m: f" T{int(m.group(1)):02d}00 ", s)
    toks, initial = [], True
    for m in _TOKEN_RX.finditer(s):
        raw = m.group(0)
        toks.append(Tok(raw, initial))
        initial = raw in (".", ";", "!", "?", ":")
    return toks


def detect_lang(toks) -> str:
    fs = [t.f for t in toks]
    score = {k: sum(f in v for f in fs) for k, v in L.LANG_HINTS.items()}
    if any(f in ("daqui", "voce", "relatorio", "nao", "feitos", "ao", "uma", "sexta", "obrigado") for f in fs): score["pt"] += 3
    if any(f in ("del", "esta", "para") for f in fs) and "nao" not in fs: score["es"] += 1
    return max(score, key=lambda k: (score[k], k == "es"))


def _num(tok: str):
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", tok): return int(re.sub(r"[.,]", "", tok))
    if re.fullmatch(r"\d+[.,]\d+", tok): return float(tok.replace(",", "."))
    if tok.isdigit(): return int(tok)
    return L.NUM_WORDS.get(tok)


def norm_token(f: str, lang: str):
    """Normalized key of a content token for equality: quantifier/number/synonym/preposition classes, plural stripped."""
    if f in L.QUANTIFIERS: return "Q:" + L.QUANTIFIERS[f]
    if f in L.UNITS and L.UNITS[f] in ("weeks", "days", "hours", "minutes", "months", "years"): return "U:" + L.UNITS[f]
    n = _num(f)
    if n is not None: return f"N:{n}"
    if f in L.SYNONYMS: return L.SYNONYMS[f]
    p = L.PREP_MAP.get(lang, {}).get(f)
    if p: return p
    if len(f) > 4 and f.endswith("es") and f[-3] in "lrnzds" and not f.endswith("ses") or f.endswith("ones"):
        g = f[:-2]
        return L.SYNONYMS.get(g, g)
    if len(f) > 3 and f.endswith("s") and not f.endswith("ss"):
        g = f[:-1]
        return L.SYNONYMS.get(g, g)
    return f


FUNCTIONAL = {"DEM", "TO", "FOR", "IN", "OF", "WITH", "BY", "ON", "FROM", "AT", "que", "that", "which", "who", "como", "as", "like", "and", "y", "e", "o", "u", "or", "of", "le", "les", "'s"}


class Ctx:
    def __init__(self, toks, lang):
        self.lang, self.flags, self.names, self.roles = lang, [], set(), set()
        self.arts = L.ARTICLES[lang] | (L.ARTICLES["es"] if lang == "pt" else set())
        for t in toks:
            if not t.initial and t.raw[:1].isupper() and t.raw.isalpha() and not t.raw.isupper() and t.f not in L.DAYS and t.f not in L.RELDAYS and t.f not in ("friday", "monday"):
                self.names.add(t.f)
            if t.f in L.ROLES: self.roles.add(t.f)


def _is_verb(t: Tok, ctx, head=False) -> bool:
    if t.f in L.NOUN_ONLY or t.f in ctx.arts: return False
    if t.f in L.MODAL_MAY | L.MODAL_MUST | L.NEG_TOKENS: return False
    return L.verb_action(t.f) is not None


def _verb_after_conj(t, ctx) -> bool:
    return ctx.lang == "en" and t.f in L.EN_IMPERATIVE_NOUNS and L.verb_action(t.f) is not None


def _skip_pre(toks, i, ctx):
    """Index of the first token of a clause that is a verb, skipping fillers / negation / modal markers; None if the clause is not verbal."""
    j = i
    while j < len(toks) and (toks[j].f in L.NEG_TOKENS or toks[j].f in L.FILLER_WORDS or toks[j].f in L.MODAL_MAY | L.MODAL_MUST | L.FIRST_ADVERBS
                              or toks[j].f in L.SEQ_ADVERBS or toks[j].f in ("por", "favor", "also")):
        j += 1
    return j if j < len(toks) and (_is_verb(toks[j], ctx, True) or (j > i and _verb_after_conj(toks[j], ctx)) or (j == i and i > 0 and _verb_after_conj(toks[j], ctx))) else None


def _split_steps(toks, ctx):
    """Main clause tokens -> [(step tokens, order)] using before/after+infinitive, sequence adverbs and 'and'+verb. order = relation to previous step."""
    toks = [t for k, t in enumerate(toks) if not (t.f in L.ONLY_WORDS and k + 1 < len(toks) and (toks[k + 1].f in L.SEQ_ADVERBS or toks[k + 1].f in ("antes", "despues", "depois", "before", "after")))]
    n = len(toks)
    # 1) before/after + infinitive  =>  ordered pair
    for i in range(n):
        for key, rel in (("antes de", "before"), ("despues de", "after"), ("depois de", "after"), ("before", "before"), ("after", "after"), ("tras", "after"), ("prior to", "before")):
            kt = tuple(key.split())
            if tuple(t.f for t in toks[i:i + len(kt)]) == kt and i + len(kt) < n:
                nxt = toks[i + len(kt)]
                if L.verb_action(nxt.f) and (re.search(r"(?:ar|er|ir|or|ing|arse|erse|irse|lo|la|los|las|se|me)$", nxt.f)) and nxt.f not in L.NOUN_ONLY:
                    lead = all(t.f in L.FILLER_WORDS or t.f in L.FIRST_ADVERBS for t in toks[:i])
                    j = i + len(kt)
                    if lead:
                        k = next((x for x in range(j, n) if toks[x].f == ","), n)
                        sub, main = toks[j:k], toks[k + 1:]
                    else:
                        main, sub = toks[:i], toks[j:]
                        while main and main[-1].f in (",", "y", "and", "e"): main = main[:-1]
                    if not main or not sub: continue
                    a, b = (main, sub) if rel == "before" else (sub, main)
                    out = _split_steps(a, ctx)
                    tail = _split_steps(b, ctx)
                    if tail: tail[0] = (tail[0][0], "explicit")
                    return out + tail
    # 2) sequence adverbs / and+verb / comma+verb
    steps, cur, order, i = [], [], None, 0
    first_adverb = False
    while i < n:
        f = toks[i].f
        if f in L.FIRST_ADVERBS and i + 1 < n and _skip_pre(toks, i + 1, ctx) is not None and not cur:
            first_adverb = True; i += 1; continue
        if f in L.SEQ_ADVERBS and not cur and not (i + 1 < n and toks[i + 1].f in ("de", "del", "que", "do")):
            order = "explicit"; i += 1
            if i < n and toks[i].f == ",": i += 1
            continue
        if f in L.SEQ_ADVERBS and not (i + 1 < n and toks[i + 1].f in ("de", "del", "que", "do")) and cur:
            steps.append((cur, order)); cur, order = [], "explicit"; i += 1; continue
        if f in L.CONJ_AND | {","} and cur and i + 1 < n:
            j = i + 1
            if toks[j].f == "," : j += 1
            seq = False
            while j < n and toks[j].f in L.SEQ_ADVERBS: j += 1; seq = True
            if j < n and toks[j].f in L.FIRST_ADVERBS: j += 1
            if _skip_pre(toks, j, ctx) is not None and (f != "," or True):
                steps.append((cur, order)); cur, order = [], "explicit" if seq else "implicit"; i = j; continue
        cur.append(toks[i]); i += 1
    if cur: steps.append((cur, order))
    if first_adverb and steps:  # 'primero ... luego ...' makes the order explicit for the second step too
        steps = [(s, o if o is None else "explicit") for s, o in steps]
    return steps


def parse(text: str, today=None) -> SemanticObject:
    clean, findings = sanitize_input(text)
    toks = tokenize(clean)
    lang = detect_lang(toks)
    ctx = Ctx(toks, lang)
    flags = [("SANITIZER", f) for f in findings]
    norm = tuple(t.f for t in toks if t.f not in PUNCT)
    # sentences
    sents, cur = [], []
    for t in toks:
        if t.f in (";", ".", "!", "?") : 
            if cur: sents.append(cur); cur = []
        else: cur.append(t)
    if cur: sents.append(cur)
    steps = []
    for si, sent in enumerate(sents):
        steps += _parse_sentence(sent, ctx, len(steps))
        if si + 1 < len(sents) and _find_cond(sent, ctx) and _find_cond(sent, ctx)["start"] == 0 and not _find_cond(sents[si + 1], ctx):
            ctx.flags.append(("AMBIGUOUS_COND_SCOPE", "does the leading condition also cover the next ';' clause?"))
    # pronouns that need earlier steps
    _resolve_refs(steps, ctx)
    if len({a.type for a in ctx.flags}) if False else False: pass
    flags += ctx.flags
    for k, s in enumerate(steps):
        s.idx = k
        s.atoms = [Atom(a.type, a.value, a.span, a.provenance, k, a.confidence, a.candidates) for a in s.atoms]
    if not steps:
        flags.append(("UNREPRESENTABLE_EMPTY", "no content"))
    return SemanticObject(text, lang, steps, flags, norm)


# ------------------------------------------------------------------------------------------------------------------ conditions
def _find_cond(toks, ctx):
    """Return (kind, neg, start, end_of_marker, clause_end, bounded_by_comma) for the first conditional marker, else None."""
    n = len(toks)
    fs = [t.f for t in toks]
    for i in range(n):
        for phrases, kind, neg in ((L.COND_NEC, "nec", False), (L.COND_UNLESS, "suff", True), (L.COND_SUFF, "suff", False)):
            for ph in sorted(phrases, key=len, reverse=True):
                if tuple(fs[i:i + len(ph)]) == ph:
                    if ph == ("se",) and lang_not_pt(ctx) and not (i + 1 < n and fs[i + 1] in ("o", "a", "os", "as", "um", "uma", "nao", "ele", "ela", "voce", "houver", "for", "estiver") and i == 0): continue
                    if ph == ("once",) and True: continue
                    if ph in (("cuando",), ("when",), ("quando",), ("whenever",)) and False: continue
                    if ph == ("if",) or ph == ("si",):
                        pass
                    j = i + len(ph)
                    k = next((x for x in range(j, n) if fs[x] == ","), None)
                    return dict(kind=kind, neg=neg, start=i, mstart=j, end=(k if k is not None else n), bounded=k is not None, phrase=ph)
    return None


def lang_not_pt(ctx): return ctx.lang != "pt"


def _cond_bag(toks, ctx, neg):
    bag, n_neg, conj = [], 0, set()
    for t in toks:
        if t.f in L.NEG_TOKENS and t.f not in ("nadie", "nada", "nobody", "nothing"): n_neg += 1; continue
        if t.f in ctx.arts or t.f in L.COPULA[ctx.lang] or t.f in L.COPULA["en"] or t.f in L.FILLER_WORDS or t.f in PUNCT or t.f in ("se",): continue
        if t.f in L.CONJ_AND: conj.add("and"); bag.append("AND"); continue
        if t.f in L.CONJ_OR: conj.add("or"); bag.append("OR"); continue
        bag.append(norm_token(t.f, ctx.lang))
    if len(conj) == 2: ctx.flags.append(("AMBIGUOUS_GROUPING", "and/or mixed inside one condition"))
    return (neg ^ (n_neg % 2 == 1)), tuple(sorted(bag)), bool(conj)


def _parse_sentence(sent, ctx, base):
    toks = list(sent)
    cond = _find_cond(toks, ctx)
    cond_atom, before_tokens, after_tokens, mode = None, toks, [], None
    if cond:
        ctoks = toks[cond["mstart"]:cond["end"]]
        if not ctoks:
            ctx.flags.append(("UNREPRESENTABLE_ELSE", "bare 'if not' / empty condition")); ctoks = []
        elif ctoks[0].f == "no" and len(ctoks) == 1:
            ctx.flags.append(("UNREPRESENTABLE_ELSE", "else-branch"))
        neg, bag, _ = _cond_bag(ctoks, ctx, cond["neg"])
        cond_atom = Atom("COND", (cond["kind"], neg, bag))
        pre, post = toks[:cond["start"]], toks[cond["end"] + 1:] if cond["bounded"] else []
        if cond["start"] == 0:
            main_scope, rest = post, []          # leading condition: guards everything after the comma
            groups = [(main_scope, True)]
        elif cond["bounded"] and post:
            groups = [(pre, False), (post, True)]  # '... y, si X, haz Y': guards only what follows
        else:
            while pre and pre[-1].f == ",": pre = pre[:-1]
            groups = [(pre, True)]
            if len(_split_steps(pre, ctx)) > 1 and not cond["bounded"]:
                ctx.flags.append(("AMBIGUOUS_COND_SCOPE", "trailing condition after several actions"))
    else:
        groups = [(toks, False)]
    steps = []
    for gtoks, guarded in groups:
        while gtoks and gtoks[0].f == ",": gtoks = gtoks[1:]
        while gtoks and gtoks[-1].f == ",": gtoks = gtoks[:-1]
        if not gtoks: continue
        for stoks, order in _split_steps(gtoks, ctx):
            s = _parse_step(stoks, ctx)
            s.order = order if steps or order else None
            if guarded and cond_atom:
                ca = cond_atom
                only_act = [a for a in s.atoms if a.type == "ONLY" and a.value == "ACTION"]
                if only_act and ca.value[0] == "suff":          # 'only deploy when X' == 'deploy only when X'
                    ca = Atom("COND", ("nec",) + ca.value[1:]); s.atoms = [a for a in s.atoms if a not in only_act]
                s.atoms.append(ca)
            steps.append(s)
    # relation to the previous sentence's last step: plain juxtaposition = implicit order
    if steps and base > 0 and steps[0].order is None: steps[0].order = "implicit"
    return steps


# ------------------------------------------------------------------------------------------------------------------ step
def _parse_step(toks, ctx) -> Step:
    st = Step(0)
    A, items = st.atoms, st.items
    lang, n, i = ctx.lang, len(toks), 0
    neg = 0; deontic = "DO"; avoid = False; adv_fillers = False
    not_true = litotes = not_required = False
    qty_acc = []          # (mode, value, unit, prov)
    quant = []
    action_set = False
    flags_here = []
    fs = [t.f for t in toks]

    def at(i, phrase): return tuple(fs[i:i + len(phrase)]) == phrase

    def read_number(j):
        """Parse a number (digits / words / 'N dozen' / 'a couple') at j -> (value, next_j, ambiguous)"""
        if j >= n: return None
        if tuple(fs[j:j + 2]) in L.PAIR_WORDS: return (2, j + 2, True)
        if fs[j] in L.MULTIPLIERS and fs[j] not in ("hundred", "thousand"): return (L.MULTIPLIERS[fs[j]], j + 1, False)
        v = _num(fs[j])
        if v is None: return None
        j += 1
        if j < n and fs[j] in L.MULTIPLIERS: v = v * L.MULTIPLIERS[fs[j]]; j += 1
        return (v, j, False)

    def read_unit(j):
        if j + 1 < n and (fs[j], fs[j + 1]) in L.BIZ: return "business_days", j + 2
        if j < n and fs[j] in L.UNITS: return L.UNITS[fs[j]], j + 1
        if j < n and fs[j] in ("de", "of") and j + 1 < n and fs[j + 1] in L.UNITS: return L.UNITS[fs[j + 1]], j + 2
        if j + 1 < n and fs[j] in ("de", "of") and fs[j + 1] not in PUNCT and fs[j + 1] not in ctx.arts and not _is_verb(toks[j + 1], ctx) and fs[j + 1] not in L.DAYS | L.RELDAYS.keys():
            return norm_token(fs[j + 1], lang), j + 2
        return None, j

    def time_value(j):
        """Value of a time expression at j -> (value, next_j, kind) or None"""
        while j < n and (fs[j] in ctx.arts or fs[j] in ("proximo", "proxima", "next") and False): j += 1
        if j >= n: return None
        nxt_flag = fs[j] in L.NEXT_WORDS
        jj = j + 1 if nxt_flag else j
        if jj < n and (fs[jj] in L.DAYS or fs[jj] in L.DAYS_PT_FEIRA):
            d = L.DAYS.get(fs[jj]) or L.DAYS_PT_FEIRA[fs[jj]]
            if jj + 1 < n and fs[jj + 1] in ("feira",): jj += 1
            return (("next:" if nxt_flag else "") + d, jj + 1, "day")
        if fs[j] == "pasado" and j + 1 < n and fs[j + 1] == "manana": return ("day_after_tomorrow", j + 2, "rel")
        if fs[j] in L.RELDAYS and not (fs[j] == "manana" and j > 0 and fs[j - 1] in ("la", "de", "por")):
            return (L.RELDAYS[fs[j]], j + 1, "rel")
        if re.fullmatch(r"T\d{4}", toks[j].raw): return (toks[j].raw, j + 1, "clock")
        if j + 1 < n and fs[j] in ("dia", "day", "dia") and _num(fs[j + 1]) is not None: return (f"d{_num(fs[j + 1])}", j + 2, "date")
        if fs[j] in ("las", "la") and j + 1 < n and _num(fs[j + 1]) is not None and _num(fs[j + 1]) <= 24 and j + 2 < n and fs[j + 2] not in L.UNITS:
            return (f"T{int(_num(fs[j + 1])):02d}00", j + 2, "clock")
        r = read_number(j)
        if r:
            u, k = read_unit(r[1])
            if u: return ((r[0], u), k, "span")
        return None

    def opaque_until(j, stop_conj=True):
        out = []
        while j < n and fs[j] not in PUNCT and not (stop_conj and fs[j] in L.CONJ and out):
            if fs[j] not in ctx.arts and fs[j] not in L.COPULA[lang] and fs[j] not in L.COPULA["en"]:
                out.append(norm_token(fs[j], lang))
            j += 1
        return tuple(out), j

    prov_default = "DEFAULTED"
    prev_modalish = False
    while i < n:
        was_modalish, prev_modalish = prev_modalish, False
        f, raw = fs[i], toks[i].raw
        if f in PUNCT: i += 1; continue
        # --- litotes / double negation / not-required
        hit = next((p for p in L.LITOTES if at(i, p)), None)
        if hit:
            litotes = True
            if hit[0] in ("nunca", "never", "jamas"): A.append(Atom("TIME", ("recurring", "always"), (i, i + len(hit))))      # 'never fail to X' = 'always X'
            i += len(hit); continue
        hit = next((p for p in L.NOT_REQUIRED if at(i, p)), None)
        if hit: not_required = True; i += len(hit); continue
        hit = next((p for p in L.NOT_TRUE if at(i, p)), None)
        if hit and not not_true: not_true = True; i += len(hit); continue
        # --- quantity phrases (must precede negation: 'no more than')
        mm = next(((p, m) for p, m in L.QTY_PHRASES if at(i, p)), None)
        if mm:
            p, mode = mm
            r = read_number(i + len(p))
            if r:
                v, j, amb = r
                u, j2 = read_unit(j)
                if u is None and j2 < n and fs[j2] not in PUNCT and fs[j2] not in L.CONJ and fs[j2] not in ctx.arts and fs[j2] not in L.DAYS and fs[j2] not in L.RELDAYS and not _is_verb(toks[j2], ctx):
                    u = norm_token(fs[j2], lang); j2 += 1
                qty_acc.append((mode, v, u, "EXPLICIT"))
                if amb: flags_here.append(("AMBIGUOUS_QUANTITY", "'un par' / 'a couple'"))
                i = j2; continue
            if mode in ("approx",) and p in (("unos",), ("unas",)): items.append(("TOK", norm_token(f, lang))); i += 1; continue
        # 'hasta N' as a quantity ceiling (vs 'hasta el viernes' as time)
        if f in ("hasta", "ate", "until", "up") and i + 1 < n:
            r = read_number(i + 1 + (1 if f == "up" and fs[i + 1] == "to" else 0))
            if r and not (f in ("hasta", "ate") and time_value(i + 1) and time_value(i + 1)[2] in ("clock", "date", "day")):
                v, j, amb = r; u, j2 = read_unit(j)
                if u in ("hours", "minutes", "days", "weeks", "months", "years") and False: pass
                else:
                    if u is None and j2 < n and fs[j2] not in PUNCT and fs[j2] not in L.CONJ and not _is_verb(toks[j2], ctx):
                        u = norm_token(fs[j2], lang); j2 += 1
                    qty_acc.append(("at_most", v, u, "EXPLICIT")); i = j2; continue
        if f == "entre" or f == "between":
            r = read_number(i + 1)
            if r:
                v1, j, _ = r
                if j < n and fs[j] in ("y", "and", "e"):
                    r2 = read_number(j + 1)
                    if r2:
                        v2, k, _ = r2; u, k2 = read_unit(k)
                        if u is None and k2 < n and fs[k2] not in PUNCT and fs[k2] not in L.CONJ and not _is_verb(toks[k2], ctx): u = norm_token(fs[k2], lang); k2 += 1
                        qty_acc.append(("range", (v1, v2), u, "EXPLICIT")); i = k2; continue
        if (f == "sin" and fs[i:i + 2] == ["sin", "falta"]) or fs[i:i + 2] in (["without", "fail"], ["sem", "falta"]): i += 2; continue
        if f in L.FRACTION_WORDS or fs[i:i + 2] == ["cuarto", "de"]:
            ctx.flags.append(("UNREPRESENTABLE_FRACTION", "fraction word (half / quarter): quantity form not modelled")); i += 1; continue
        ph = next(((p, k) for p, k in L.PHASE_PHRASES if at(i, p)), None)
        if ph:
            p, kind = ph; bag, k2 = opaque_until(i + len(p), stop_conj=False)
            A.append(Atom("TIME", ("at_phase", ("bag", kind) + bag), (i, k2), "EXPLICIT", 0, 0.6)); i = k2; continue
        # --- time relations
        tr = next(((p, rel) for p, rel in L.TIME_REL if at(i, p)), None)
        if tr and not (tr[1] == "within" and tr[0] == ("in",) and not (i + 1 < n and read_number(i + 1))) and not (tr[0] == ("by",) and not time_value(i + 1)):
            p, rel = tr
            j = i + len(p)
            tv = time_value(j)
            if tv:
                val, k, kind = tv
                cands = frozenset({"until"}) if rel == "before" and p[0] in ("antes", "before") else frozenset({"before"}) if rel == "until" and p[0] in ("hasta", "ate", "until", "till") else frozenset()
                alt = frozenset((rel2, val) for rel2 in cands) | (frozenset({(rel, val[5:])}) if isinstance(val, str) and val.startswith("next:") else frozenset())
                A.append(Atom("TIME", (rel, val), (i, k), "EXPLICIT", 0, 1.0, alt))
                i = k; continue
            bag, k = opaque_until(j)
            if bag and p not in (("from",), ("by",), ("in",)):
                cands = frozenset()
                A.append(Atom("TIME", (rel, ("bag",) + bag), (i, k), "EXPLICIT", 0, 0.6))
                i = k; continue
        # --- recurrence: 'cada N unit', 'every day', 'todos los lunes', 'cada semestre', 'de forma semestral', 'weekly'
        if f in ("cada", "every", "each", "todos", "todas") and i + 1 < n:
            j = i + 1
            if fs[j] in ("los", "las", "os", "as", "the"): j += 1
            rn = read_number(j) if j < n else None
            if rn and rn[1] < n and fs[rn[1]] in L.UNITS and L.UNITS[fs[rn[1]]] in ("weeks", "days", "hours", "minutes", "months", "years"):
                A.append(Atom("TIME", ("recurring", (rn[0], L.UNITS[fs[rn[1]]])), (i, rn[1] + 1))); i = rn[1] + 1; continue
            if j < n and fs[j] in L.SPECIAL_PERIODS:
                A.append(Atom("TIME", ("recurring", L.SPECIAL_PERIODS[fs[j]]), (i, j + 1))); i = j + 1; continue
            if j < n and fs[j] in L.DAYS:
                A.append(Atom("TIME", ("recurring", L.DAYS[fs[j]]), (i, j + 1))); i = j + 1; continue
            if j < n and (fs[j] in L.RECUR_KEY or fs[j] in L.UNITS):
                key = (1, "night") if fs[j] in L.RECUR_KEY else (1, L.UNITS[fs[j]])
                alt = frozenset({("recurring", (1, "days"))}) if key == (1, "night") else frozenset({("recurring", (1, "night"))}) if key == (1, "days") else frozenset()
                A.append(Atom("TIME", ("recurring", key), (i, j + 1), "EXPLICIT", 0, 1.0, alt)); i = j + 1; continue
        if f in L.RECUR_WORDS:
            key = L.RECUR_WORDS[f]
            alt = frozenset({("recurring", (1, "days"))}) if key == (1, "night") else frozenset({("recurring", (1, "night"))}) if key == (1, "days") else frozenset()
            A.append(Atom("TIME", ("recurring", key), (i, i + 1), "EXPLICIT", 0, 1.0, alt)); i += 1; continue
        if f in L.RECUR_ADJ and i > 0 and fs[i - 1] in L.RECUR_CUE | {"de", "con"} and any(w in L.RECUR_CUE for w in fs[max(0, i - 3):i]):
            alt = frozenset({("recurring", L.RECUR_ADJ_CANDS[f])}) if f in L.RECUR_ADJ_CANDS else frozenset()
            # the cue words ('de forma') were already pushed to items: take them back, they are part of this construction
            while items and items[-1] in (("TOK", "OF"), ("TOK", "forma"), ("TOK", "manera"), ("TOK", "periodicidad"), ("TOK", "frecuencia"), ("TOK", "WITH")): items.pop()
            A.append(Atom("TIME", ("recurring", L.RECUR_ADJ[f]), (i, i + 1), "EXPLICIT", 0, 1.0, alt)); i += 1; continue
        if f in ("pronto", "soon", "asap"): A.append(Atom("TIME", ("vague", "soon"), (i, i + 1))); i += 1; continue
        # --- pure time words without a relation: 'el viernes', 'hoy', clock
        tv = time_value(i) if (f in L.DAYS or f in L.RELDAYS or f in L.NEXT_WORDS or re.fullmatch(r"T\d{4}", raw)) else None
        if tv:
            val, k, kind = tv
            rel = "at"
            A.append(Atom("TIME", (rel, val), (i, k), "EXPLICIT", 0, 1.0, frozenset({(rel, val[5:])}) if isinstance(val, str) and val.startswith("next:") else frozenset())); i = k; continue
        if f in ctx.arts and i + 1 < n and (fs[i + 1] in L.DAYS or fs[i + 1] in L.NEXT_WORDS):
            i += 1; continue
        # --- exceptions / without / only
        ex = next((p for p in L.EXCEPT_WORDS if at(i, p)), None)
        if ex:
            j = i + len(ex); k = j; bag = []
            while k < n and fs[k] not in PUNCT and not (bag and (fs[k] in L.MODAL_MUST | L.MODAL_MAY or (_is_verb(toks[k], ctx) and fs[k] not in L.NOUN_ONLY))):
                if fs[k] not in ctx.arts and fs[k] not in L.COPULA[lang] and fs[k] not in L.COPULA["en"]: bag.append(norm_token(fs[k], lang))
                k += 1
            A.append(Atom("EXCEPT", tuple(sorted(bag)), (i, k))); i = k; continue
        if f in L.EXEMPT_WORDS and items:
            taken = [items.pop()]
            if items and items[-1] == ("TOK", "WITH"): items.pop()
            A.append(Atom("EXCEPT", tuple(sorted(t[1] for t in taken)), (i, i + 1))); i += 1; continue
        if f in L.WITHOUT_WORDS and i + 1 < n:
            bag, k = opaque_until(i + 1, stop_conj=False)
            A.append(Atom("WITHOUT", tuple(sorted(bag)), (i, k))); i = k; continue
        if f in L.ONLY_WORDS or (f == "so" and lang == "pt"):
            j = i + 1
            while j < n and (fs[j] in ctx.arts or fs[j] in L.PREPS_ALL or fs[j] in ("a", "al", "se")): j += 1
            focus = norm_token(fs[j], lang) if j < n else None
            if j < n and _is_verb(toks[j], ctx) and not action_set: focus = "ACTION"
            A.append(Atom("ONLY", focus, (i, i + 1))); i += 1; continue
        # --- 'no one' = none (must precede the bare number 'one')
        if f == "no" and i + 1 < n and fs[i + 1] in ("one", "body"):
            quant.append("none"); i += 2; continue
        # --- negation / deontic words
        if f in ("ni", "nem"): neg = max(neg, 1) if neg == 0 else neg; prev_modalish = was_modalish; i += 1; continue
        if f in L.QUANTIFIERS and f not in ("cada", "each"):
            quant.append(L.QUANTIFIERS[f]); i += 1
            if f in ("nadie", "nobody", "ninguem"): pass
            continue
        if f in ("cada", "each") : quant.append("each"); i += 1; continue
        if f in L.NEG_TOKENS and f not in ("nada",):
            nxt = toks[i + 1].f if i + 1 < n else ""
            if action_set and not (nxt in L.MODAL_MAY | L.MODAL_MUST or L.verb_action(nxt) and nxt not in L.NOUN_ONLY):
                items.append(("TOK", "NEG")); i += 1; continue          # local negation of a modifier ('no confidenciales'), not of the whole instruction
            neg += 1; prev_modalish = True; i += 1; continue
        if f in L.PROHIBITED: deontic = "DONT"; prev_modalish = True; i += 1; continue
        if f in L.AVOID and not action_set: avoid = True; prev_modalish = True; i += 1; continue
        if f in L.MODAL_MAY: deontic = "MAY" if deontic == "DO" else deontic; prev_modalish = True; i += 1; continue
        if f in L.MODAL_MUST: prev_modalish = True; i += 1; continue
        if f in L.MODAL_ADVISE: deontic = "ADVISE"; prev_modalish = True; i += 1; continue
        # --- ordinals (adverb 'primero' already removed during step splitting)
        if f in ("mas", "more") and i + 1 < n and fs[i + 1] in ("reciente", "recientes", "recent", "antiguo", "antigo", "antiguos") and fs[i + 1] in L.ORDINALS:
            A.append(Atom("ORD", L.ORDINALS[fs[i + 1]], (i, i + 2), "EXPLICIT")); items.append(("ORD", L.ORDINALS[fs[i + 1]])); i += 2; continue
        if f in L.FIRST_ADVERBS and (i + 1 >= n or fs[i + 1] in PUNCT or fs[i + 1] in L.CONJ) and not (i > 0 and fs[i - 1] in ctx.arts):
            items.append(("TOK", "FIRST")); i += 1; continue                  # 'ship X first' = priority adverb, not the ordinal 'first'
        if f in L.ORDINALS and not (f in L.FIRST_ADVERBS and i == 0 and i + 1 < n and _is_verb(toks[i + 1], ctx)):
            v = L.ORDINALS[f]
            cands = frozenset({"most_recent"}) if v == "last" else frozenset({"last"}) if v == "most_recent" else frozenset({"oldest"}) if v == 1 else frozenset({1}) if v == "oldest" else frozenset()
            A.append(Atom("ORD", v, (i, i + 1), "EXPLICIT", 0, 1.0, cands)); items.append(("ORD", v)); i += 1; continue
        if re.fullmatch(r"ORD\d+", raw): v = int(raw[3:]); A.append(Atom("ORD", v, (i, i + 1))); items.append(("ORD", v)); i += 1; continue
        # --- verbs
        if not action_set and (was_modalish or not items) and _is_verb(toks[i], ctx, True):
            act = L.verb_action(f)
            A.append(Atom("ACTION", act, (i, i + 1)))
            action_set = True
            for cl in L.clitics_of(f):
                if cl == "me": A.append(Atom("RECIPIENT", "speaker", (i, i + 1)))
                elif cl in ("le", "les"): A.append(Atom("REF", "io", (i, i + 1), "INFERRED", 0, 0.5, frozenset({"unresolved"})))
                elif cl in ("lo", "la", "los", "las"): A.append(Atom("REF", "do", (i, i + 1), "INFERRED", 0, 0.5, frozenset({"unresolved"})))
            i += 1; continue
        if action_set and f in ("y", "and", "e"):
            if any(at(i + 1, p) for p, _ in L.QTY_PHRASES): i += 1; continue          # 'at least 10 AND at most 20' is one range, not a list
            items.append(("TOK", "AND")); i += 1; continue
        # --- bare number (implicit exactness)
        r = read_number(i) if (_num(f) is not None and f not in ("un", "una", "uno", "um", "uma")) or tuple(fs[i:i + 2]) in L.PAIR_WORDS or (f in ("docena", "docenas", "dozen", "duzia", "duzias")) else None
        if r and isinstance(_num(f), int) and 1900 <= _num(f) <= 2100 and read_unit(r[1])[0] is None:
            items.append(("TOK", f"N:{_num(f)}")); i += 1; continue          # a year, not a quantity
        if r:
            v, j, amb = r; u, j2 = read_unit(j)
            if u is None and j2 < n and fs[j2] not in PUNCT and fs[j2] not in L.CONJ and fs[j2] not in ctx.arts and not _is_verb(toks[j2], ctx) and fs[j2] not in L.PREPS_ALL:
                u = norm_token(fs[j2], lang); j2 += 1
            qty_acc.append(("exact_implicit", v, u, prov_default))
            if amb: flags_here.append(("AMBIGUOUS_QUANTITY", "'un par' / 'a couple'"))
            i = j2; continue
        # --- pronouns
        if raw.lower() == "él" or f in ("ella", "ellos", "ellas", "she", "he", "they", "ele", "ela", "su", "sus", "his", "her", "their", "seu", "sua", "seus", "suas", "its", "eles", "elas"):
            g = "m" if (raw.lower() == "él" or f in ("he", "ele", "ellos", "eles", "his")) else "f" if f in ("ella", "she", "ela", "ellas", "elas", "her") else "x"   # English his/her are gendered; Spanish/Portuguese su/seu are not
            A.append(Atom("REF", f"person:{g}", (i, i + 1), "INFERRED", 0, 0.4, frozenset({"unresolved"}))); i += 1; continue
        if f in ("it", "them"): A.append(Atom("REF", "do", (i, i + 1), "INFERRED", 0, 0.5, frozenset({"unresolved"}))); i += 1; continue
        # --- fillers, articles, copula
        if f in ctx.arts or f in L.COPULA[lang] or f in L.COPULA["en"] or f in L.FILLER_WORDS or f in L.SE_TOKENS or f in ("por", "favor") and fs[i:i + 2] == ["por", "favor"]:
            if f in ("por", "favor") : i += 1; continue
            i += 1; continue
        if (f == "sin" and fs[i:i + 2] == ["sin", "falta"]) or fs[i:i + 2] in (["without", "fail"], ["sem", "falta"]): i += 2; continue
        if f in L.DEMONSTRATIVES: items.append(("TOK", "DEM")); i += 1; continue
        # --- content token
        if not toks[i].initial and raw[:1].isupper() and raw.isalpha() and not raw.isupper() and f in ctx.names:
            items.append(("NAME", f))
        else:
            items.append(("TOK", norm_token(f, lang)))
        i += 1

    # ----- compose deontic status
    modal_seen = any(w in L.MODAL_MAY | L.MODAL_MUST | L.PROHIBITED | L.MODAL_ADVISE for w in fs)
    double_neg_modal = neg >= 2 and modal_seen and not litotes and not not_true and not not_required
    if litotes: neg = 0; deontic = "DO"
    if quant and "none" in quant and neg == 0:
        neg = 1
    if neg % 2 == 1:
        deontic = {"DO": "DONT", "MAY": "DONT", "ADVISE": "DISCOURAGE", "DONT": "DONT"}.get(deontic, deontic)
    cands = frozenset()
    if avoid: deontic = "DISCOURAGE"
    if deontic == "DISCOURAGE": cands = frozenset({"DONT"})
    if deontic == "ADVISE": cands = frozenset({"DO"})
    if neg % 2 == 1 and deontic == "DONT" and not any(w in L.PROHIBITED for w in fs) and not any(w in ("nunca", "jamas", "never") for w in fs):
        gt = [q for q in qty_acc if q[0] in ("greater_than", "less_than")]
        if len(gt) == 1:             # 'do not send MORE THAN 10' == 'send AT MOST 10'
            q = gt[0]; qty_acc[qty_acc.index(q)] = ("at_most" if q[0] == "greater_than" else "at_least", q[1], q[2], "INFERRED"); deontic = "DO"; neg = 0
            quant[:] = ["each" if x in ("none", "any") else x for x in quant]       # 'no bus may carry more than 40' = each bus carries at most 40
    if neg % 2 == 1 and any(a.type == "TIME" and a.value[0] == "until" for a in A):
        flags_here.append(("AMBIGUOUS_NEGATED_TEMPORAL", "negation over 'until' (not-until = after?)"))
    if double_neg_modal:       # 'no está permitido no registrar' = must register, not 'permitted': the two negations do NOT simply cancel
        cands = frozenset({"DO", "MAY", "DONT"}) - {deontic}
        flags_here.append(("AMBIGUOUS_DOUBLE_NEGATION", "two negations around a modal: obligation / permission / prohibition are all reachable"))
    if not_required: deontic = "NOT_REQUIRED"
    if not_true:
        if deontic == "DO": deontic = "NOT_REQUIRED"
        elif deontic in ("DONT",):
            deontic, cands = "DO", frozenset({"MAY"}); flags_here.append(("AMBIGUOUS_DOUBLE_NEGATION", "negated modal under 'it is not true that'"))
        else: flags_here.append(("AMBIGUOUS_DOUBLE_NEGATION", "nested negation"))
    A.append(Atom("DEONTIC", deontic, (0, n), "EXPLICIT", 0, 1.0, cands))
    # quantifier / negation scope
    for q in dict.fromkeys(quant):
        if q == "all" and neg % 2 == 1 and deontic in ("DONT", "DISCOURAGE"):
            A.append(Atom("QUANT", "not_all", (0, n), "EXPLICIT", 0, 0.5, frozenset({"any"}))); flags_here.append(("AMBIGUOUS_NEGATED_ALL", "not-all vs none"))
        elif q == "some" and neg % 2 == 1:
            A.append(Atom("QUANT", "not_all", (0, n), "INFERRED"))         # 'some visitors do NOT need X' = 'not every visitor needs X'
        elif q in ("none", "any") and neg % 2 == 1:
            A.append(Atom("QUANT", "any", (0, n)))
        else:
            A.append(Atom("QUANT", q, (0, n)))
    # merge at_least + at_most with the same unit into a range (canonicalization)
    lo = [q for q in qty_acc if q[0] == "at_least"]; hi = [q for q in qty_acc if q[0] == "at_most"]
    if len(lo) == 1 and len(hi) == 1 and (lo[0][2] == hi[0][2] or None in (lo[0][2], hi[0][2])):
        qty_acc = [q for q in qty_acc if q not in (lo[0], hi[0])] + [("range", (lo[0][1], hi[0][1]), lo[0][2] or hi[0][2], "EXPLICIT")]
    for mode, v, u, prov in qty_acc:
        A.append(Atom("QTY", (mode, v, u), (0, n), prov))
    if neg % 2 == 1 and deontic == "DONT" and ("TOK", "AND") in items and not any(w in ("neither", "nor", "ni", "nem") for w in fs):
        flags_here.append(("AMBIGUOUS_NEGATED_COORDINATION", "'not A and B': neither, or not both?"))
    if any(a.type == "TIME" and a.value[1] == "T0000" for a in A) and any(a.type == "TIME" and a.value[1] in set(L.DAYS.values()) | {"next:" + d for d in L.DAYS.values()} for a in A):
        flags_here.append(("AMBIGUOUS_MIDNIGHT", "midnight of <day>: start or end of that day?"))
    and_pos = [k for k, it in enumerate(items) if it == ("TOK", "AND")]
    if and_pos and any(q[0] in ("less_than", "greater_than", "at_least", "at_most") and q[2] in ("years", "months", "days", "weeks") for q in qty_acc):
        flags_here.append(("AMBIGUOUS_MODIFIER_SCOPE", "a trailing modifier after 'A y B': does it apply to both?"))
    for code, d in flags_here: ctx.flags.append((code, d))
    # same-step recipient / reference simplification
    return st


def _resolve_refs(steps, ctx):
    """Resolve clitic / pronoun references against earlier steps. Resolved => INFERRED item; otherwise the REF atom stays AMBIGUOUS."""
    people = ctx.names | ctx.roles
    for k, s in enumerate(steps):
        new_atoms = []
        for a in s.atoms:
            if a.type != "REF": new_atoms.append(a); continue
            if a.value == "do":
                prev = steps[k - 1] if k > 0 else None
                objs = [it for it in (prev.items if prev else []) if it[0] == "TOK" and it[1] not in FUNCTIONAL and it[1] != "AND"] if prev else []
                objs = list(dict.fromkeys(objs))
                if len(objs) == 1:
                    s.items.append(("TOK", objs[0][1])); new_atoms.append(Atom("REF", "do", a.span, "INFERRED", 0, 0.9)); continue
                new_atoms.append(a)
            elif a.value == "io":
                has_to = any(it[0] == "NAME" for it in s.items) or any(it[0] == "TOK" and it[1] in ctx.roles for it in s.items)
                new_atoms.append(Atom("REF", "io", a.span, "INFERRED", 0, 0.9) if has_to else a)
            else:  # person pronoun. Gendered forms (he/she/él/ella) are never auto-resolved: a name's gender is unknown, so a single candidate is not evidence.
                gendered = a.value in ("person:m", "person:f")
                if len(people) == 1 and not gendered: new_atoms.append(Atom("REF", a.value, a.span, "INFERRED", 0, 0.8))
                else:
                    new_atoms.append(Atom("REF", a.value, a.span, "INFERRED", 0, 0.3, frozenset(sorted(people)) or frozenset({"unresolved"})))
        s.atoms = new_atoms
