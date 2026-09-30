"""Semantic Lab text rendering (CLI + shared by the web server). Presentation only: no semantics here."""
from aixl import compare, semantic_diff, detect_ambiguity, to_aixl
from aixl.core.comparator import DIM_LABEL

DIMS = ["actions", "entities", "data", "time", "location", "constraints", "conditions", "negation", "references", "quantities", "output", "modifiers"]
SHOW = {"actions": "ACTION", "entities": "ENTITY", "data": "DATA", "time": "TIME", "location": "LOCATION", "constraints": "CONSTRAINT",
        "conditions": "CONDITION", "negation": "NEGATION", "references": "REFERENCE", "quantities": "QUANTITY", "output": "OUTPUT", "modifiers": "MODIFIER"}


def bar(x: float, width: int = 10) -> str:
    n = round(x * width)
    return "█" * n + "░" * (width - n)


def lab_view(a: str, b: str) -> str:
    r = compare(a, b)
    pct = round(r.similarity * 100)
    lines = ["AIXL Semantic Lab", "=" * 60, f"TEXT A: {a}", f"TEXT B: {b}", "-" * 60, "Semantic Equivalence", f"{bar(r.similarity)} {pct}%",
             "DRIFT", r.drift_level.replace("_DRIFT", "") if r.differences else "NONE", ""]
    for d in DIMS:
        v = r.per_dimension.get(d)
        if v is not None:
            lines.append(f"  {SHOW[d]:<11} {'✓' if v == 1.0 else '✗'}")
    lines += ["", semantic_diff(a, b), "",
              "VERDICT: " + ("SEMANTICALLY EQUIVALENT" if r.equivalent else "NOT EQUIVALENT" + (" — CRITICAL_SEMANTIC_DRIFT" if r.critical_changes else "")),
              f"AIXL A: {to_aixl(a)}", f"AIXL B: {to_aixl(b)}"]
    return "\n".join(lines)
