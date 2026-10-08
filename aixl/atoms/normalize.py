"""AIXL 0.4 graph normal form (ADR-021): collapses REPRESENTATIONAL alternatives so that two valid extractions of the same text compare equal.
Everything here must preserve meaning; every rule carries its evidence (data/aliases.json: texts it was mined from) and is checked by
(a) held-out agreement lift and (b) the false-equivalence rate (different texts must not collapse to the same graph).
Stages: 1 lemma normalization of `x:` concepts, 2 alias table (concept -> canonical concept, same atom type only), 3 structural rewrites."""
import json
import os
import re

from aixl.atoms.schema import AtomGraph

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "aliases.json")
NORMAL_FORM_VERSION = "0.0"


def singular(w: str) -> str:
    if len(w) > 4 and w.endswith("ies"): return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is", "ous")): return w[:-1]
    return w


def lemma(c: str) -> str:
    """x:Press_Releases -> x:press_release (plural stripped on the last segment only)."""
    if not c.startswith("x:"): return c
    body = re.sub(r"[^a-z0-9_]+", "_", c[2:].lower()).strip("_")
    parts = body.split("_")
    parts[-1] = singular(parts[-1])
    return "x:" + "_".join(parts)


def load_tables(path: str = _DATA) -> dict:
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return dict(version=NORMAL_FORM_VERSION, aliases={}, rewrites=[])


class Normalizer:
    def __init__(self, tables: dict | None = None, stages=("lemma", "alias", "learn", "rewrite")):
        self.t = tables if tables is not None else load_tables()
        self.stages = stages
        from aixl.atoms import registry as R
        self.aliases = {k: v for k, v in self.t.get("aliases", {}).items()}
        # an extension lemma that the registry has since learned becomes its registry id (the registry itself is the table)
        self.learned = {f"{c['type']}:x:{c['id'].split('.', 1)[1].lower()}": c["id"] for c in R.LEARNED}

    @property
    def version(self) -> str:
        return self.t.get("version", NORMAL_FORM_VERSION)

    def _rename(self, g, learn: bool):
        for a in g.atoms:
            if a.concept:
                a.concept = self.aliases.get(f"{a.type}:{a.concept}", a.concept) if not learn else self.learned.get(f"{a.type}:{a.concept}", a.concept)

    def __call__(self, g: AtomGraph) -> AtomGraph:
        out = AtomGraph.from_dict(g.to_dict())
        out.unrepresented = list(g.unrepresented)
        if "lemma" in self.stages:
            for a in out.atoms:
                if a.concept: a.concept = lemma(a.concept)
        if "alias" in self.stages: self._rename(out, False)       # curated/judged synonym table (same atom type only)
        if "rewrite" in self.stages:
            from aixl.atoms import rewrite as RW
            RW.apply(out, self.t.get("rewrites", []))             # compounds are built from extension names, so this runs BEFORE learned ids replace them
        if "learn" in self.stages: self._rename(out, True)
        return out
