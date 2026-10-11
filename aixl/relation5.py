"""Prompt-maestro 1.1 (Módulo 3) five-way relation + (Módulo 8) typed error record, derived from the existing Verdict.

No new semantics: this only RELABELS what `compare_texts` already proved. It never upgrades a verdict:
EQUIVALENT is emitted iff the underlying verdict is EQUIVALENT. Anything not derivable is UNDETERMINED (fail-closed).
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field

RELATIONS = ("EQUIVALENT", "COMPATIBLE", "PARTIAL", "CONTRADICTORY", "UNDETERMINED")


@dataclass
class Relation:
    relation: str
    direction: str | None = None      # PARTIAL: "B_EXTENDS_A" | "A_EXTENDS_B"
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def classify(verdict) -> Relation:
    """verdict: aixl.semantic.model.Verdict (or anything with .verdict and .diffs[].type)."""
    if verdict.verdict == "EQUIVALENT":
        return Relation("EQUIVALENT", reason="all compared elements match")
    if verdict.verdict != "NOT_EQUIVALENT":
        why = (verdict.unresolved or ["no proof either way"])[0]
        return Relation("UNDETERMINED", reason=str(why))
    kinds = {d.type for d in verdict.diffs}
    if "CONTRADICTION" in kinds or "DISTORTION" in kinds:
        return Relation("CONTRADICTORY", reason="same element, incompatible value/polarity")
    if kinds == {"ADDITION"}:
        return Relation("PARTIAL", "B_EXTENDS_A", "B states requirements A does not")
    if kinds == {"LOSS"}:
        return Relation("PARTIAL", "A_EXTENDS_B", "A states requirements B does not")
    if kinds == {"ADDITION", "LOSS"}:
        return Relation("COMPATIBLE", reason="each side adds something, nothing conflicts (jointly executable; NOT equivalent)")
    return Relation("UNDETERMINED", reason=f"diff types {sorted(kinds)} do not map to a relation")


ERROR_TYPES = ("EQUIVALENCE_ERROR", "NEGATION_LOSS", "CONSTRAINT_LOSS", "ENTITY_MISMATCH", "RELATION_LOSS", "AMBIGUOUS_ATOM",
               "DECODE_ERROR", "TOKEN_REGRESSION", "INTEROPERABILITY_FAILURE", "FALSE_CONFIDENCE")


@dataclass
class ErrorRecord:
    case_id: str
    input: str
    expected_meaning: str
    encoded_form: str = ""
    reconstructed_meaning: str = ""
    error_type: str = ""
    root_cause: str = ""
    correction: str = ""
    regression_test: str = ""
    version: str = ""
    ts: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.error_type and self.error_type not in ERROR_TYPES:
            raise ValueError(f"unknown error_type {self.error_type!r}")


def error_from_relation(case_id: str, a: str, b: str, expected: str, got: Relation, version: str = "") -> ErrorRecord | None:
    """Record only real mismatches. Unsafe direction (claiming EQUIVALENT wrongly) is FALSE_CONFIDENCE; safe miss is EQUIVALENCE_ERROR."""
    if expected == got.relation:
        return None
    unsafe = got.relation == "EQUIVALENT" and expected != "EQUIVALENT"
    return ErrorRecord(case_id, f"{a} || {b}", expected, reconstructed_meaning=got.relation,
                       error_type="FALSE_CONFIDENCE" if unsafe else "EQUIVALENCE_ERROR",
                       root_cause=got.reason, version=version)


def append_jsonl(rec: ErrorRecord, path: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
