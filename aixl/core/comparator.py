"""FASE 7 — SemanticComparator: layered comparison of two SemanticGraphs on their CANONICAL forms.

Equivalence is EXACT on the canonical form (any difference in any dimension => not equivalent). The similarity score
is a weighted, configurable, experimental metric for graded reporting; it is not "truth" (spec §14).
"""
from dataclasses import dataclass, field

from aixl.core.semantic_graph import SemanticGraph
from aixl.core.ontology import DIMENSIONS, ANTONYM_ACTIONS, load_config, rank

DERIVED = {"intent", "goal"}      # derived from actions/negation/entities: scored, never reported as an independent difference
DIM_LABEL = {"negation": "NEGATION", "actions": "ACTION", "quantities": "QUANTITY"}


def _label(dim: str) -> str:
    return DIM_LABEL.get(dim, dim.upper())


def _fmt(v) -> str:
    if isinstance(v, tuple):
        return ",".join(v) if v else "NOT_SPECIFIED"
    return v if v else "NOT_SPECIFIED"


@dataclass
class Difference:
    field: str
    source: str
    target: str
    kind: str          # changed | added | removed | order
    severity: str      # MINOR | MODERATE | MAJOR | CRITICAL
    detail: str = ""

    def to_dict(self):
        return dict(field=self.field, source=self.source, target=self.target, kind=self.kind, severity=self.severity, detail=self.detail)


@dataclass
class ComparisonResult:
    equivalent: bool
    similarity: float
    drift: float
    drift_level: str
    differences: list = field(default_factory=list)
    critical_changes: list = field(default_factory=list)
    per_dimension: dict = field(default_factory=dict)
    explanation: str = ""
    warnings: list = field(default_factory=list)     # §66 transparency: LOSS/UNCERTAINTY that the verdict does not show

    @property
    def diff(self) -> list:
        return [d.to_dict() for d in self.differences]

    def to_dict(self):
        d = dict(equivalent=self.equivalent, similarity=round(self.similarity, 4), drift=round(self.drift, 4),
                 drift_level=self.drift_level, differences=self.diff, critical_changes=[d.to_dict() for d in self.critical_changes],
                 per_dimension={k: (None if v is None else round(v, 3)) for k, v in self.per_dimension.items()}, explanation=self.explanation)
        if self.warnings:
            d["warnings"] = self.warnings
        return d


def _severity(dim: str, a, b, cfg: dict, acts=frozenset(), kind: str = "changed") -> tuple[str, str]:
    base = cfg["severity"].get(dim, "MAJOR")
    detail = ""
    # context-sensitive (§39, adversarial suite 2026-10-02): swapping or dropping WHO/WHAT a destructive or external
    # action applies to (recipient, id, object, "only to X" scope) is as dangerous as flipping the action itself.
    # Directional: 'added' (original -> narrower) stays at its base severity; 'removed'/'changed' escalate.
    if dim in ("references", "entities", "data") and kind in ("changed", "removed") and acts & set(cfg.get("destructive_actions", [])):
        return "CRITICAL", "target/scope of a destructive or external action changed"
    if dim in ("conditions", "constraints") and kind in ("changed", "removed") and acts & set(cfg.get("destructive_actions", [])):
        return "CRITICAL", "safeguard (condition/constraint) dropped from a destructive or external action"
    if dim == "negation":
        return "CRITICAL", "prohibition/permission changed"
    if dim == "constraints":
        keys = {x.split("=")[0] for x in set(a) ^ set(b) if "=" in x}
        hit = keys & set(cfg.get("critical_constraint_keys", []))
        if hit:
            return "CRITICAL", "critical constraint: " + ",".join(sorted(hit))
    if dim == "actions":
        changed = set(a) ^ set(b)
        destr = set(cfg.get("destructive_actions", []))
        if changed & destr:
            return "CRITICAL", "destructive action involved"
        for x, y in ANTONYM_ACTIONS:
            if (x in a and y in b) or (y in a and x in b):
                return "CRITICAL", f"opposite actions {x}/{y}"
    return base, detail


def compare_graphs(ga: SemanticGraph, gb: SemanticGraph, config: dict | None = None, today=None) -> ComparisonResult:
    cfg = config or load_config()
    A, B = ga.canonical(today=today), gb.canonical(today=today)
    res = compare_canonical(A, B, cfg)
    for side, g in (("a", ga), ("b", gb)):
        terms = g.meta.get("unrecognized")
        if terms:
            res.warnings.append({"type": "UNRECOGNIZED_TERMS", "side": side, "terms": list(terms),
                                 "note": "object noun(s) outside the lexicon were NOT represented; equivalence/partial verdicts may overstate agreement"})
    for side, c in (("a", A), ("b", B)):
        if not c["actions"]:
            res.warnings.append({"type": "NO_ACTION_RECOGNIZED", "side": side, "severity": "BLOCKING",
                                 "note": "no action was recognised in this text, so an 'equivalent' verdict proves nothing (insufficient context)"})
    return res


def compare_canonical(A: dict, B: dict, config: dict | None = None) -> ComparisonResult:
    """Same comparison as compare_graphs, but on two already-computed canonical() dicts directly —
    used by the negotiation protocol (aixl/negotiation.py) to re-score a receiver's belief state after
    it adopts a sender's answer for one disputed dimension, without reconstructing a SemanticGraph."""
    cfg = config or load_config()
    diffs: list[Difference] = []
    per: dict = {}
    acts = frozenset(A["actions"]) | frozenset(B["actions"])
    for dim in DIMENSIONS:
        va, vb = A[dim], B[dim]
        if not va and not vb:
            per[dim] = None
            continue
        if isinstance(va, tuple) and isinstance(vb, tuple):
            sa, sb = set(va), set(vb)
            per[dim] = len(sa & sb) / len(sa | sb) if (sa | sb) else 1.0
            if sa != sb and dim not in DERIVED:
                kind = "changed" if (sa - sb and sb - sa) else ("removed" if sa - sb else "added")
                sev, det = _severity(dim, sa, sb, cfg, acts, kind)
                diffs.append(Difference(_label(dim), _fmt(va), _fmt(vb), kind, sev, det))
            elif sa == sb and va != vb and dim in ("actions", "location"):
                per[dim] = 0.5
                diffs.append(Difference(_label(dim), _fmt(va), _fmt(vb), "order", "MODERATE", "same items, different order"))
        else:
            per[dim] = 1.0 if va == vb else 0.0
            if va != vb and dim not in DERIVED:
                kind = "changed" if (va and vb) else ("removed" if va else "added")
                sev, det = _severity(dim, va, vb, cfg, acts, kind)
                diffs.append(Difference(_label(dim), _fmt(va), _fmt(vb), kind, sev, det))
    w = cfg["weights"]
    num = sum(w[d] * s for d, s in per.items() if s is not None)
    den = sum(w[d] for d, s in per.items() if s is not None)
    sim = num / den if den else 1.0
    worst = max((rank(d.severity) for d in diffs), default=0)
    level = ["NO_DRIFT", "MINOR_DRIFT", "MODERATE_DRIFT", "MAJOR_DRIFT", "CRITICAL_DRIFT"][worst]
    crit = [d for d in diffs if d.severity == "CRITICAL"]
    expl = "identical canonical semantics" if not diffs else "; ".join(f"{d.field}: {d.source} -> {d.target} ({d.severity})" for d in diffs)
    return ComparisonResult(not diffs, sim, 1.0 - sim if diffs else 0.0, level, diffs, crit, per, expl)


def format_diff(ga: SemanticGraph, gb: SemanticGraph, result: ComparisonResult | None = None) -> str:
    """Human readable SEMANTIC DIFF (spec §22)."""
    r = result or compare_graphs(ga, gb)
    A, B = ga.canonical(), gb.canonical()
    changed = {d.field: d for d in r.differences}
    lines = ["SEMANTIC DIFF"]
    for dim in DIMENSIONS:
        if dim in ("intent", "goal"):
            continue
        if not A[dim] and not B[dim]:
            continue
        lab = _label(dim)
        lines.append(lab)
        if lab in changed:
            d = changed[lab]
            lines += ["  changed:", f"    {d.source}", "    →", f"    {d.target}", f"  severity: {d.severity}" + (f" ({d.detail})" if d.detail else "")]
        else:
            lines.append(f"  unchanged: {_fmt(A[dim])}")
    lines += ["RESULT", "  SEMANTIC DRIFT DETECTED (" + r.drift_level + ")" if r.differences else "  No meaningful differences detected."]
    return "\n".join(lines)
