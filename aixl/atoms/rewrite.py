"""Structural rewrite rules of the normal form (data-driven, see normalize.py). A rule is a dict {name, op, ...}; ops are registered below."""
OPS = {}


def op(name):
    def deco(f): OPS[name] = f; return f
    return deco


def apply(g, rules) -> None:
    for r in rules:
        OPS[r["op"]](g, r)


def base_name(c: str) -> str:
    """lexical name of a concept for building compounds: x:foo_bar -> foo_bar; registry id -> first English form."""
    if c.startswith("x:"): return c[2:]
    from aixl.atoms import registry as R
    k = R.concept(c)
    return (k["lex"]["en"][0] if k and k["lex"].get("en") else c.split(".")[-1].lower()).replace(" ", "_").lower()


@op("compound_collapse")
def compound_collapse(g, rule):
    """ENTITY(head) with a LEAF modifier (PROPERTY via HAS_PROPERTY, or ENTITY via OF; both of them x:/registry, no quantifier, no other relations)
    -> ENTITY x:<modifier>_<head>. Repeats until stable. Only extension heads are renamed (registry heads keep their id).
    Meaning-preserving by construction: the modifier is absorbed into the concept name that the compound-annotator already used."""
    changed = True
    while changed:
        changed = False
        ids = g.by_id()
        for e in list(g.atoms):
            if e.type != "ENTITY" or not e.concept or not e.concept.startswith("x:") or e.id not in ids: continue
            for s, r, d in list(g.relations):
                if s != e.id or r not in ("HAS_PROPERTY", "OF") or d not in ids: continue
                m = ids[d]
                if m.type not in ("PROPERTY", "ENTITY") or (r == "HAS_PROPERTY") != (m.type == "PROPERTY") or not m.concept: continue
                if m.polarity != "+" or m.scope != e.scope or m.status != "explicit": continue
                if any((a == d or b == d) and (a, rr, b) != (s, r, d) for a, rr, b in g.relations): continue     # m must be a leaf
                e.concept = "x:" + base_name(m.concept) + "_" + e.concept[2:]
                g.atoms = [a for a in g.atoms if a.id != d]
                g.relations = [t for t in g.relations if d not in (t[0], t[2])]
                changed = True
                break
            if changed: break


@op("unit_alias")
def unit_alias(g, rule):
    """QUANTITY units: x:degree_celsius -> x:celsius, x:kilogram -> x:kg ... (rule["map"], mined from dev unit disagreements with identical mode and number).
    Pure naming: the number and the mode are never touched."""
    m = rule["map"]
    for a in g.atoms:
        if a.type == "QUANTITY" and isinstance(a.value, dict) and a.value.get("unit") in m:
            a.value = dict(a.value, unit=m[a.value["unit"]])
