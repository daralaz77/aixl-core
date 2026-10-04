"""0.3-R semantic comparison — FAIL-CLOSED three-state verdict.

  NOT_EQUIVALENT  only when a MODELLED slot definitively differs (deontic, quantity mode/value, time relation/value, condition,
                  exception, only-focus, ordinal, action, sequence order, or one side adds/loses content tokens).
  EQUIVALENT      only when EVERY slot is equal, no ambiguity/unrepresentable flag is open, and the ordered content items match.
  INCONCLUSIVE    everything else: an alternative reading overlaps, a lexical gap (different words, no synonym), an unresolved
                  reference, an unsupported construct. The reasons are listed in `unresolved`; nothing is guessed.
Equivalence is NEVER derived from a score or from similar wording (master prompt §2, §27)."""
import itertools
from collections import Counter
from aixl.semantic.model import Atom, Diff, Verdict
from aixl.semantic.parser import parse, FUNCTIONAL
from aixl.semantic import lexicon as L

SEVERITY = {"DEONTIC": "CRITICAL", "COND": "CRITICAL", "EXCEPT": "CRITICAL", "WITHOUT": "CRITICAL", "ACTION": "CRITICAL", "ONLY": "MAJOR", "TIME": "MAJOR",
            "QTY": "MAJOR", "ORD": "MAJOR", "QUANT": "MAJOR", "RECIPIENT": "MAJOR", "SEQUENCE": "MAJOR", "STEP": "MAJOR", "ITEMS": "MODERATE"}
SYMMETRIC_ACTIONS = {"COMPARE"}
KNOWN_UNITS = set(L.UNITS.values()) | {"business_days"}


class _Acc:
    def __init__(self): self.diffs, self.unres, self.warn = [], [], []

    def diff(self, path, typ, a, b, kind=None):
        self.diffs.append(Diff(path, typ, a, b, SEVERITY.get(kind or path.split(".")[-1].split("[")[0].upper(), "MAJOR")))

    def un(self, reason): self.unres.append(reason)


def _cmp(a: Atom | None, b: Atom | None):
    """EQ | DIFF | UNRES | MISSING for two atoms of the same type."""
    if a is None and b is None: return "EQ"
    if a is None or b is None: return "MISSING"
    if a.value == b.value and a.candidates == b.candidates: return "EQ"
    if a.alternatives & b.alternatives: return "UNRES"
    return "DIFF"


def _of(step, t): return step.get(t)


def _qty_cmp(a, b, acc, p):
    va, vb = sorted(a, key=lambda x: x.span), sorted(b, key=lambda x: x.span)
    if not va and not vb: return
    if len(va) == len(vb) > 1 and Counter(x.value for x in va) == Counter(x.value for x in vb) and [x.value for x in va] != [x.value for x in vb]:
        acc.un("same quantities in a different order: roles may be swapped"); return
    if len(va) != len(vb):
        acc.diff(p, "LOSS" if len(va) > len(vb) else "ADDITION", [x.value for x in va], [x.value for x in vb], "QTY"); return
    for x, y in zip(va, vb):
        (m1, v1, u1), (m2, v2, u2) = x.value, y.value
        if x.value == y.value: continue
        if v1 == v2 and u1 == u2 and {m1, m2} == {"exact", "exact_implicit"}:
            acc.un("quantity exactness is implicit on one side (bare number vs 'exactly')"); continue
        if u1 != u2 and (u1 in KNOWN_UNITS and u2 in KNOWN_UNITS or v1 == v2 and m1 == m2 and u1 and u2 and False):
            acc.diff(p + ".unit", "SUBSTITUTION", u1, u2, "QTY"); continue
        if u1 != u2 and not (u1 in KNOWN_UNITS and u2 in KNOWN_UNITS): acc.un(f"quantity unit differs lexically ({u1} / {u2})");
        if v1 != v2 or m1 != m2 and not {m1, m2} == {"exact", "exact_implicit"}:
            acc.diff(p + ".mode" if m1 != m2 else p + ".value", "DISTORTION", x.value, y.value, "QTY")


def _is_span(x): return x.value[0] not in ("recurring", "at_phase") and isinstance(x.value[1], tuple) and len(x.value[1]) == 2 and x.value[1][0] != "bag"


def _time_cmp(a, b, acc, p):
    if not a and not b: return
    if (any(_is_span(x) for x in a) and b and not any(_is_span(y) for y in b)) or (any(_is_span(y) for y in b) and a and not any(_is_span(x) for x in a)):
        acc.un("relative span (in N days) vs calendar time: the reference date is unknown"); return
    if len(a) != len(b):
        acc.diff(p, "LOSS" if len(a) > len(b) else "ADDITION", [x.value for x in a], [x.value for x in b], "TIME"); return
    rest_b = list(b)
    for x in a:
        m = next((y for y in rest_b if y.value == x.value and y.candidates == x.candidates), None)
        if m is not None: rest_b.remove(m); continue
        # best partner: same relation first, else first remaining
        y = next((y for y in rest_b if y.value[0] == x.value[0]), rest_b[0])
        rest_b.remove(y)
        r = _cmp(x, y)
        vx, vy = x.value[1], y.value[1]
        opaque = (vx != vy) and (any(isinstance(v, tuple) and v and v[0] == "bag" for v in (vx, vy)) or "soon" in (vx, vy))
        if r == "UNRES" or opaque:
            acc.un(f"time reading not provable ({x.value} vs {y.value})")
        else:
            acc.diff(p, "DISTORTION", x.value, y.value, "TIME")


def _cond_cmp(a, b, acc):
    ca, cb = (a[0].value if a else None), (b[0].value if b else None)
    if ca is None and cb is None: return
    if ca is None or cb is None:
        acc.diff("cond", "LOSS" if cb is None else "ADDITION", ca, cb, "COND"); return
    (k1, n1, g1), (k2, n2, g2) = ca, cb
    if k1 != k2: acc.diff("cond.kind", "DISTORTION", k1, k2, "COND"); return
    if g1 == g2:
        if n1 != n2: acc.diff("cond.polarity", "DISTORTION", n1, n2, "COND")
        return
    only_conn = Counter(g1) - Counter(g2), Counter(g2) - Counter(g1)
    if all(set(c) <= {"AND", "OR"} for c in only_conn) and (only_conn[0] or only_conn[1]):
        acc.diff("cond.connective", "DISTORTION", g1, g2, "COND"); return
    acc.un(f"condition wording differs ({g1} / {g2})")


def _set_slot(a, b, acc, name, typ):
    ca, cb = (a[0].value if a else None), (b[0].value if b else None)
    if ca is None and cb is None: return
    if ca is None or cb is None: acc.diff(name.lower(), "LOSS" if cb is None else "ADDITION", ca, cb, typ); return
    if ca != cb: acc.un(f"{name.lower()} wording differs ({ca} / {cb})")


def _items_cmp(ia, ib, acc, act_a, soft=False, other_slots=(frozenset(), frozenset()), person_ref=(False, False)):
    """soft=True when a pronoun or a generic (light) verb may be standing in for content: a content difference is then only INCONCLUSIVE."""
    ia = [it for it in ia if it[0] != "ORD"]; ib = [it for it in ib if it[0] != "ORD"]
    if ia == ib: return
    ma, mb = Counter(ia), Counter(ib)
    if ma == mb:
        def groups(seq):
            gs, cur = [], []
            for it in seq:
                if it == ("TOK", "AND"): gs.append(tuple(cur)); cur = []
                else: cur.append(it)
            gs.append(tuple(cur)); return sorted(gs)
        if any(it == ("TOK", "AND") for it in ia) and groups(ia) == groups(ib): return
        acc.un("same words in a different order: roles may be swapped"); return
    ea, eb = ma - mb, mb - ma
    sa = [x for x in ea if x[0] == "NAME" or (x[0] == "TOK" and x[1].startswith("N:"))]
    sb = [x for x in eb if x[0] == "NAME" or (x[0] == "TOK" and x[1].startswith("N:"))]
    if sa and sb and not soft:
        acc.diff("items.reference", "SUBSTITUTION", sorted(sa), sorted(sb), "ORD"); return
    if soft and (ea or eb):
        acc.un("a pronoun or a light verb may stand in for the differing content"); return
    sets_a, sets_b = set(ia), set(ib)
    def is_new(x, other, slots):          # a repetition of something already said, or said in another slot, is ellipsis, not addition
        return x[1] not in FUNCTIONAL and x != ("TOK", "AND") and x not in other and x[1] not in slots
    PREPS = {"TO", "IN", "FOR", "WITH", "ON", "OF", "FROM", "AT", "BY"}
    KNOWN = set(L.SYNONYMS.values())
    def anchored(extra, ctx_items):        # does the extra material clearly ADD information (vs. a paraphrase marker / filler / adjective)?
        content = [x for x in extra if x[1] not in FUNCTIONAL and x != ("TOK", "AND")]
        return any(x[0] == "NAME" or x[1] in KNOWN or str(x[1]).startswith("N:") for x in content) or (any(x[1] in PREPS for x in extra) and bool(content))
    if not ea and eb and person_ref[0] and ("TOK", "OF") in eb:
        acc.un("a possessive ('su') on one side may stand for the 'of X' phrase on the other"); return
    if ea and not eb and person_ref[1] and ("TOK", "OF") in ea:
        acc.un("a possessive ('su') on one side may stand for the 'of X' phrase on the other"); return
    if not ea and eb:
        content = [x for x in eb if is_new(x, sets_a, other_slots[0])]
        if content and anchored(list(eb), ib): acc.diff("items", "ADDITION", None, sorted(content), "ITEMS")
        elif content: acc.un(f"extra words {sorted(content)} may be a paraphrase marker, not new information")
        else: acc.un("only function words / repeated words differ (ellipsis or distribution)")
        return
    if ea and not eb:
        content = [x for x in ea if is_new(x, sets_b, other_slots[1])]
        if content and anchored(list(ea), ia): acc.diff("items", "LOSS", sorted(content), None, "ITEMS")
        elif content: acc.un(f"words {sorted(content)} missing on one side may be a paraphrase marker, not lost information")
        else: acc.un("only function words / repeated words differ (ellipsis or distribution)")
        return
    acc.un(f"content words differ with no known synonym ({sorted(ea)} / {sorted(eb)})")


def _content(st, with_ord=True):
    return {(f"ORD:{k}" if t == "ORD" else k) for t, k in st.items if t in ("TOK", "NAME") + (("ORD",) if with_ord else ()) and k not in FUNCTIONAL and k != "AND"}


def _slot_tokens(st):
    out = {a.value[2] for a in st.get("QTY") if a.value[2]}
    for t in st.get("TIME"):                       # a recurrence / phase already says its unit and period words
        v = t.value[1]
        if t.value[0] == "recurring" and isinstance(v, tuple): out.add("U:" + v[1])
        if t.value[0] == "at_phase": out |= {x for x in v[2:]}
    for c in st.get("COND"): out |= set(c.value[2])
    for e in st.get("EXCEPT") + st.get("WITHOUT"): out |= set(e.value)
    return out


def _reliable_filter(x, y, acc):
    """A definitive difference is only trusted when the two texts are otherwise explained by each other.
    * presence mismatch (one side has the slot, the other lacks it): the side that lacks it must say nothing the other does not say,
      otherwise its extra words may be expressing the same slot with a construction the parser does not model.
    * value conflict (both have the slot): neither side may carry unexplained content words.
    Ordinals are the slot itself when the difference is on a reference, so they are not counted as unexplained words there."""
    def unexplained(with_ord):
        gx, gy = getattr(x, 'global_content', set()), getattr(y, 'global_content', set())
        return (_content(x, with_ord) - _content(y, with_ord) - _slot_tokens(y) - gy, _content(y, with_ord) - _content(x, with_ord) - _slot_tokens(x) - gx)
    keep, shown = [], set()
    paths = [d.path for d in acc.diffs]
    contraposition = any(p.endswith("deontic") for p in paths) and any(p.startswith("cond") for p in paths)
    gx_all, gy_all = getattr(x, "global_content", set()), getattr(y, "global_content", set())
    for d in acc.diffs:
        if d.path == "items": keep.append(d); continue
        if contraposition and (d.path.endswith("deontic") or d.path.startswith("cond")):
            acc.unres.append(f"{d.path}: polarity changed together with a condition: the same rule may be written by contraposition"); continue
        if getattr(acc, "cross", False) and d.path.endswith("deontic"):
            acc.unres.append(f"{d.path}: the set restriction is written differently, which also changes polarity ('only X' vs 'nobody except X')"); continue
        ord_ = not d.path.endswith(".ref")
        strip = (lambda S: S) if ord_ else (lambda S: {k for k in S if not str(k).startswith("ORD:")})
        ua, ub = unexplained(with_ord=ord_)
        if not ord_:        # an ordinal's antecedent is mentioned elsewhere in the same text ('la primera' = the flour), so repetition does not explain it
            ua = _content(x, False) - _content(y, False) - _slot_tokens(y); ub = _content(y, False) - _content(x, False) - _slot_tokens(x)
        ga = strip(gx_all) - strip(gy_all) - _slot_tokens(y)        # words A says anywhere that B never says
        gb = strip(gy_all) - strip(gx_all) - _slot_tokens(x)
        if d.type == "LOSS": ok = not ub and not gb         # original (A) had it, B lacks it: B must say nothing unexplained anywhere
        elif d.type == "ADDITION": ok = not ua and not ga  # B has it, A lacks it
        else: ok = not ua and not ub
        if ok: keep.append(d)
        else: acc.unres.append(f"{d.path} differs but the other text has unexplained words ({sorted(ua | ub)}): possibly the same idea in another construction")
    acc.diffs = keep


def _step_cmp(x, y, acc, k):
    outer, acc = acc, _Acc()
    a_act, b_act = x.one("ACTION"), y.one("ACTION")
    try:
        _step_cmp_inner(x, y, acc, k, a_act, b_act)
        _reliable_filter(x, y, acc)
    finally:
        weak = _cmp(a_act, b_act) in ("MISSING", "UNRES") or (_cmp(a_act, b_act) == "DIFF" and any(a.value in L.GENERIC_ACTIONS for a in (a_act, b_act)))
        if weak and acc.diffs:          # parse of the action is unreliable on one side: slot differences may be artefacts
            acc.unres.append("slot differences suppressed: action not recognized / generic on one side")
            acc.diffs = []
        outer.diffs += acc.diffs; outer.unres += acc.unres; outer.warn += acc.warn


def _step_cmp_inner(x, y, acc, k, a_act, b_act):
    r = _cmp(a_act, b_act)
    if r == "DIFF":
        if a_act.value in L.GENERIC_ACTIONS or b_act.value in L.GENERIC_ACTIONS: acc.un(f"generic action ({a_act.value} / {b_act.value})")
        else: acc.diff(f"step[{k}].action", "SUBSTITUTION", a_act.value, b_act.value, "ACTION")
    elif r == "MISSING": acc.un("action not recognized on one side (verb kept as content word)")
    elif r == "UNRES": acc.un("action readings overlap")
    r = _cmp(x.one("DEONTIC"), y.one("DEONTIC"))
    if r == "DIFF": acc.diff(f"step[{k}].deontic", "DISTORTION", x.one("DEONTIC").value, y.one("DEONTIC").value, "DEONTIC")
    elif r == "UNRES": acc.un(f"deontic strength not provable ({x.one('DEONTIC').value} / {y.one('DEONTIC').value})")
    if bool(x.get("QTY")) != bool(y.get("QTY")) and (x.get("QUANT") or y.get("QUANT")):
        acc.un("a number on one side vs a vague quantifier ('several', 'all') on the other")
    else:
        _qty_cmp(x.get("QTY"), y.get("QTY"), acc, f"step[{k}].qty")
    # quantifier word
    qa, qb = x.get("QUANT"), y.get("QUANT")
    if bool(qa) != bool(qb): acc.un("quantifier explicit on one side only")
    else:
        for u, v in zip(sorted(qa, key=lambda a: str(a.value)), sorted(qb, key=lambda a: str(a.value))):
            rr = _cmp(u, v)
            if rr == "DIFF": acc.diff(f"step[{k}].quant", "DISTORTION", u.value, v.value, "QUANT")
            elif rr == "UNRES": acc.un(f"quantifier reading not provable ({u.value} / {v.value})")
    _time_cmp(x.get("TIME"), y.get("TIME"), acc, f"step[{k}].time")
    _cond_cmp(x.get("COND"), y.get("COND"), acc)
    ra_t = {t for t in ("EXCEPT", "ONLY", "WITHOUT") if x.get(t)}; rb_t = {t for t in ("EXCEPT", "ONLY", "WITHOUT") if y.get(t)}
    rel = lambda st: any(it in (("TOK", "NEG"), ("TOK", "que"), ("TOK", "that"), ("TOK", "which"), ("TOK", "who")) for it in st.items)
    cross = bool(ra_t and rb_t and ra_t != rb_t) or bool((ra_t and not rb_t and rel(y)) or (rb_t and not ra_t and rel(x)))
    acc.cross = cross
    if cross: acc.un(f"set restriction expressed differently ({sorted(ra_t)} / {sorted(rb_t)}); not proven to select the same set")
    else:
        _set_slot(x.get("EXCEPT"), y.get("EXCEPT"), acc, "EXCEPT", "EXCEPT")
        _set_slot(x.get("WITHOUT"), y.get("WITHOUT"), acc, "WITHOUT", "WITHOUT")
    oa, ob = (x.get("ONLY"), y.get("ONLY")) if not cross else ([], [])
    if bool(oa) != bool(ob): acc.diff(f"step[{k}].only", "LOSS" if not ob else "ADDITION", oa[0].value if oa else None, ob[0].value if ob else None, "ONLY")
    elif oa and oa[0].value != ob[0].value: acc.un(f"'only' focus differs ({oa[0].value} / {ob[0].value})")
    ra, rb = x.get("RECIPIENT"), y.get("RECIPIENT")
    if bool(ra) != bool(rb): acc.diff(f"step[{k}].recipient", "LOSS" if not rb else "ADDITION", ra[0].value if ra else None, rb[0].value if rb else None, "RECIPIENT")
    # ordinals: positional
    ords_a = [a for a in sorted(x.get("ORD"), key=lambda a: a.span)]
    ords_b = [a for a in sorted(y.get("ORD"), key=lambda a: a.span)]
    if len(ords_a) != len(ords_b) and (({a.value for a in ords_a} | {c for a in ords_a for c in a.candidates}) & {a.value for a in ords_b}
                                       or ({a.value for a in ords_b} | {c for a in ords_b for c in a.candidates}) & {a.value for a in ords_a}):
        acc.un("ordinal readings overlap but are expressed with a different number of references")
    elif len(ords_a) == len(ords_b) > 1 and a_act and b_act and a_act.value == b_act.value in SYMMETRIC_ACTIONS and Counter(a.value for a in ords_a) == Counter(a.value for a in ords_b):
        acc.un("argument order of a symmetric action (may or may not carry direction)")
    elif len(ords_a) != len(ords_b): acc.diff(f"step[{k}].ref", "LOSS" if len(ords_a) > len(ords_b) else "ADDITION", [a.value for a in ords_a], [a.value for a in ords_b], "ORD")
    else:
        for u, v in zip(ords_a, ords_b):
            rr = _cmp(u, v)
            if rr == "DIFF": acc.diff(f"step[{k}].ref", "SUBSTITUTION", u.value, v.value, "ORD")
            elif rr == "UNRES": acc.un(f"ordinal reading not provable ({u.value} / {v.value})")
    # unresolved / ambiguous references
    ga = {a.value[-1] for a in x.get("REF") if a.value.startswith("person:")} - {"x"}
    gb = {a.value[-1] for a in y.get("REF") if a.value.startswith("person:")} - {"x"}
    if ga and gb and ga != gb: acc.diff(f"step[{k}].ref.gender", "SUBSTITUTION", sorted(ga), sorted(gb), "RECIPIENT")     # he vs she point at different people
    for who, st in (("A", x), ("B", y)):
        for a in st.get("REF"):
            if a.ambiguous: acc.un(f"unresolved reference in {who} ({a.value})")
    for who, st in (("A", x), ("B", y)):
        for a in st.atoms:
            if a.provenance in ("INFERRED", "DEFAULTED") and not a.ambiguous: acc.warn.append(f"{who}.{a.type}={a.value} is {a.provenance.lower()}, not stated")
    amb_ref = any(a.ambiguous and a.value in ("do", "io") for st in (x, y) for a in st.get("REF"))   # object pronouns can stand in for content; possessives cannot
    generic = any(a is not None and a.value in L.GENERIC_ACTIONS for a in (a_act, b_act))
    def slot_tokens(st):
        out = {a.value[2] for a in st.get("QTY") if a.value[2]}
        for c in st.get("COND"): out |= set(c.value[2])
        for e in st.get("EXCEPT") + st.get("WITHOUT"): out |= set(e.value)
        return frozenset(out)
    gx, gy = getattr(x, "global_content", set()), getattr(y, "global_content", set())     # words said anywhere else in the same text are repetitions
    _items_cmp(x.items, y.items, acc, a_act.value if a_act else None, soft=amb_ref or generic or cross, other_slots=(slot_tokens(x) | gx, slot_tokens(y) | gy),
               person_ref=(bool([a for a in x.get('REF') if a.value.startswith('person')]), bool([a for a in y.get('REF') if a.value.startswith('person')])))


def compare(A, B) -> Verdict:
    acc = _Acc()
    if A.norm == B.norm and A.norm:
        return Verdict("EQUIVALENT", warnings=["identical message: any ambiguity is shared, not resolved"])
    sa, sb = A.steps, B.steps
    for obj in (A, B):
        allc = set().union(*[_content(s) for s in obj.steps]) if obj.steps else set()
        for s in obj.steps: s.global_content = allc
    if len(sa) == len(sb):
        probe = [_Acc() for _ in sa]
        for k, (x, y) in enumerate(zip(sa, sb)): _step_cmp(x, y, probe[k], k)
        direct_clean = all(not p.diffs and not p.unres for p in probe)
        if direct_clean or len(sa) == 1:
            for p in probe: acc.diffs += p.diffs; acc.unres += p.unres; acc.warn += p.warn
            if len(sa) > 1 and direct_clean:
                for k in range(1, len(sa)):
                    ea, eb = sa[k].order, sb[k].order
                    if ea != eb: acc.un(f"step {k}: the order is stated explicitly in one text only ({ea} / {eb}); a bare 'and' does not prove the same requirement")
        else:
            perm_ok = None
            for perm in itertools.permutations(range(len(sb))):
                if all((lambda t: not t.diffs and all(u.startswith(("unresolved reference", "a possessive")) for u in t.unres))(_probe(sa[i], sb[j])) for i, j in enumerate(perm)):
                    perm_ok = perm; break
            if perm_ok is not None and perm_ok != tuple(range(len(sb))):
                explicit = any(s.order == "explicit" for s in sa[1:] + sb[1:])
                if explicit: acc.diff("sequence", "DISTORTION", [s.idx for s in sa], list(perm_ok), "SEQUENCE")
                else: acc.un("same steps in a different order, with no explicit ordering word (and/then) on either side")
            else:
                for p in probe: acc.diffs += p.diffs; acc.unres += p.unres; acc.warn += p.warn
    else:
        small, big, lose = (sa, sb, False) if len(sa) < len(sb) else (sb, sa, True)
        matched = [any((lambda t: not t.diffs and not t.unres)(_probe(s, t)) for t in big) for s in small]
        glob = lambda o: set().union(*[_content(s) for s in o.steps]) if o.steps else set()
        lacking_unexplained = (glob(B) - glob(A)) if lose else (glob(A) - glob(B))        # the shorter text must say nothing the longer one does not
        if matched and all(matched) and not lacking_unexplained: acc.diff("steps", "LOSS" if lose else "ADDITION", len(sa), len(sb), "STEP")
        elif matched and all(matched): acc.un(f"one text has an extra step, but the other says things the first never says ({sorted(lacking_unexplained)[:4]}): possibly the same idea in another construction")
        else: acc.un(f"different number of steps ({len(sa)} / {len(sb)}) that do not align")
    for who, o in (("A", A), ("B", B)):
        for code, detail in o.flags:
            if code.startswith("UNREPRESENTABLE") or code.startswith("AMBIGUOUS") or code == "SANITIZER":
                acc.un(f"{who}: {code} ({detail})")
    flags_all = {c for o in (A, B) for c, _ in o.flags}
    if any(c.startswith("UNREPRESENTABLE") for c in flags_all) and acc.diffs:         # an unmodelled construct makes slot diffs unreliable
        acc.unres.append("slot differences suppressed: an unrepresentable construct is present"); acc.diffs = []
    if "AMBIGUOUS_MODIFIER_SCOPE" in flags_all:
        keep = [d for d in acc.diffs if not d.path.startswith("items") and "qty" not in d.path]
        if len(keep) != len(acc.diffs): acc.unres.append("differences suppressed: the scope of a trailing modifier over a coordination is ambiguous")
        acc.diffs = keep
    if "AMBIGUOUS_MIDNIGHT" in flags_all:
        keep = [d for d in acc.diffs if "time" not in d.path]
        if len(keep) != len(acc.diffs): acc.unres.append("time differences suppressed: 'midnight of <day>' is ambiguous")
        acc.diffs = keep
    if "AMBIGUOUS_NEGATED_TEMPORAL" in flags_all:
        keep = [d for d in acc.diffs if "deontic" not in d.path]
        if len(keep) != len(acc.diffs): acc.unres.append("deontic differences suppressed: negation over 'until' is ambiguous")
        acc.diffs = keep
    if "AMBIGUOUS_COND_SCOPE" in flags_all:
        keep = [d for d in acc.diffs if not d.path.startswith("cond")]
        if len(keep) != len(acc.diffs): acc.unres.append("condition differences suppressed: the condition's scope is ambiguous")
        acc.diffs = keep
    if A.lang != B.lang:                                                               # false friends: same spelling, different language
        closed = set(L.SYNONYMS.values()) | {"AND", "NEG", "DEM"} | set(v for d in L.PREP_MAP.values() for v in d.values())
        shared = {k for st in A.steps for t, k in st.items if t == "TOK" and k not in closed and not k.startswith(("N:", "Q:"))} & \
                 {k for st in B.steps for t, k in st.items if t == "TOK" and k not in closed and not k.startswith(("N:", "Q:"))}
        if shared: acc.un(f"cross-language: identical spelling is not verified to mean the same ({sorted(shared)})")
    codes = sorted(flags_all)
    if acc.diffs: return Verdict("NOT_EQUIVALENT", acc.diffs, list(dict.fromkeys(acc.unres)), list(dict.fromkeys(acc.warn)), codes)
    if acc.unres: return Verdict("INCONCLUSIVE", [], list(dict.fromkeys(acc.unres)), list(dict.fromkeys(acc.warn)), codes)
    return Verdict("EQUIVALENT", [], [], list(dict.fromkeys(acc.warn)), codes)


def _probe(x, y):
    t = _Acc(); _step_cmp(x, y, t, 0); return t


def compare_texts(a: str, b: str) -> Verdict:
    return compare(parse(a), parse(b))
