"""FASE 8 — Drift detection: how much did the meaning move between SOURCE and TARGET semantics?

Levels are derived from the highest severity among the concrete differences (configurable in data/config.json).
CRITICAL covers: negation/permission flips, quantity changes, destructive/opposite actions, critical constraints
(visibility, before/after). A drift report always carries the concrete differences (never just a label)."""
from dataclasses import dataclass, field

from aixl.core.comparator import compare_graphs
from aixl.core.semantic_graph import SemanticGraph


@dataclass
class DriftReport:
    level: str
    drift: float
    similarity: float
    differences: list = field(default_factory=list)
    critical_changes: list = field(default_factory=list)
    critical: bool = False
    explanation: str = ""

    def to_dict(self):
        return dict(level=self.level, drift=round(self.drift, 4), similarity=round(self.similarity, 4),
                    differences=[d.to_dict() for d in self.differences], critical_changes=[d.to_dict() for d in self.critical_changes],
                    flag="CRITICAL_SEMANTIC_DRIFT" if self.critical else None, explanation=self.explanation)


def detect_drift_graphs(source: SemanticGraph, target: SemanticGraph, config: dict | None = None) -> DriftReport:
    r = compare_graphs(source, target, config)
    return DriftReport(r.drift_level, r.drift, r.similarity, r.differences, r.critical_changes,
                       r.drift_level == "CRITICAL_DRIFT", r.explanation)
