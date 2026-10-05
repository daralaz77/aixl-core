"""ATOM INTEROPERABILITY FIDELITY (master prompt §46): per-dimension precision/recall/F1 of a produced AtomGraph against a gold AtomGraph.
Atoms are matched by their 1-round neighbourhood signature, so two graphs that differ only in atom ids score 1.0 everywhere."""
from collections import Counter

CORE_DIMS = ("polarity", "quantitative", "temporal", "scope", "constraint")   # safety-critical meaning: modality/negation, numbers, time, conditions/exceptions, limits
DIMENSIONS = ("identity", "value", "relation", "scope", "constraint", "polarity", "temporal", "quantitative", "reference")


def _neigh_sig(g):
    ids = g.by_id()
    out = {}
    for a in g.atoms:
        base = (a.type, a.concept or "")
        rel_out = tuple(sorted((r, ids[d].type, ids[d].concept or "") for s, r, d in g.relations if s == a.id and d in ids))
        out[a.id] = (base, rel_out)
    return out


def _prf(gold: Counter, got: Counter):
    tp = sum((gold & got).values()); g = sum(gold.values()); p = sum(got.values())
    prec = tp / p if p else (1.0 if not g else 0.0)
    rec = tp / g if g else 1.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return dict(tp=tp, gold=g, got=p, precision=round(prec, 4), recall=round(rec, 4), f1=round(f1, 4))


def _dim_items(g):
    ids = g.by_id()
    scopes = {a.id: (ids[a.scope].type, str(ids[a.scope].value)) if a.scope else None for a in g.atoms}
    dims = {d: Counter() for d in DIMENSIONS}
    def lab(a): return f"{a.type}:{a.concept or ''}"
    for a in g.atoms:
        dims["identity"][(a.type, a.concept or "")] += 1
        if a.type in ("NAME", "QUANTIFIER", "REFERENCE") or a.type == "CONDITION":
            dims["value"][(a.type, str(a.value))] += 1
        if a.type == "REFERENCE": dims["reference"][(a.type, str(a.value))] += 1
        if a.type == "QUANTITY":
            dims["quantitative"][("QTY", a.value["mode"], str(a.value["n"]), a.value["unit"])] += 1
            dims["value"][("QTY", a.value["mode"], str(a.value["n"]), a.value["unit"])] += 1
        if a.type == "TIME":
            dims["temporal"][("TIME", a.value["rel"], str(a.value["ref"]))] += 1
            dims["value"][("TIME", a.value["rel"], str(a.value["ref"]))] += 1
        if a.type == "ACTION": dims["polarity"][(a.concept, a.modality or "DO")] += 1
        elif a.polarity != "+" or a.scope: dims["polarity"][(lab(a), a.polarity)] += 1
        if a.scope: dims["scope"][("in", lab(a), scopes[a.id])] += 1
    for s, r, d in g.relations:
        a, b = ids[s], ids[d]
        item = (lab(a), r, lab(b))
        dims["relation"][item] += 1
        if r in ("EXCLUDES", "RESTRICTS_TO", "CONDITIONED_BY"): dims["scope"][("rel",) + item] += 1
        if r in ("CONSTRAINED_BY", "OUTPUT_AS"): dims["constraint"][item + ((b.value or {}).get("mode", ""),)] += 1
        if r == "REFERS_TO": dims["reference"][("refers",) + item] += 1
    return dims


def score(gold, got) -> dict:
    """-> {dimension: prf}, plus 'overall' = micro over all dimensions, and exact graph match flag by fingerprint."""
    gd, pd = _dim_items(gold), _dim_items(got)
    res = {d: _prf(gd[d], pd[d]) for d in DIMENSIONS}
    tg, tp_ = Counter(), Counter()
    for d in DIMENSIONS:
        tg.update({(d,) + k: v for k, v in gd[d].items()}); tp_.update({(d,) + k: v for k, v in pd[d].items()})
    res["overall"] = _prf(tg, tp_)
    res["exact"] = gold.fingerprint(include_unrepresented=False) == got.fingerprint(include_unrepresented=False)
    return res


def aggregate(scores: list) -> dict:
    out = {}
    for d in DIMENSIONS + ("overall",):
        tp = sum(s[d]["tp"] for s in scores); g = sum(s[d]["gold"] for s in scores); p = sum(s[d]["got"] for s in scores)
        if g == 0 and p == 0: out[d] = None; continue
        pr = tp / p if p else 0.0; rc = tp / g if g else 1.0
        out[d] = dict(precision=round(pr, 4), recall=round(rc, 4), f1=round(2 * pr * rc / (pr + rc), 4) if pr + rc else 0.0, gold=g)
    core = [d for d in CORE_DIMS if out.get(d)]
    ctp = sum(round(out[d]["recall"] * out[d]["gold"]) for d in core); cg = sum(out[d]["gold"] for d in core)
    cp = sum(round(out[d]["recall"] * out[d]["gold"] / out[d]["precision"]) if out[d]["precision"] else 0 for d in core)
    if cg:
        pr, rc = (ctp / cp if cp else 0.0), ctp / cg
        out["core"] = dict(precision=round(pr, 4), recall=round(rc, 4), f1=round(2 * pr * rc / (pr + rc), 4) if pr + rc else 0.0, gold=cg)
    out["exact_graph"] = round(sum(s["exact"] for s in scores) / len(scores), 4) if scores else None
    return out
