"""Hybrid decision (option 3 of 2026-10-03): the semantic track is a CHEAP LOSS/DISTORTION DETECTOR and a VETO; the 2-of-2 LLM arbiter
(`aixl.arbiter`, evidence in docs/EVIDENCE.md) is the only thing that can PROVE that two instructions mean the same.

  arbiter DIFFERENT                      -> DIFFERENT   (the arbiter's dissent always blocks sameness)
  arbiter SAME  + semantic NOT_EQUIVALENT-> REVIEW      (conflict: the arbiter says same, the semantic model found a definitive difference; a human decides)
  arbiter SAME  + semantic INCONCLUSIVE carrying an AMBIGUOUS_* flag
                                         -> REVIEW      (the text itself is ambiguous in a way the semantic model detected; a SAME there is a guess, not a proof)
  arbiter SAME  + semantic EQ / other INCONCL. -> SAME
  arbiter UNSURE                         -> UNSURE      (+ a hint when the semantic model suspects a difference)
  no judges supplied                     -> never SAME: NOT_EQUIVALENT -> DIFFERENT (suspected), anything else -> UNSURE

`short_circuit=True` skips the judges when the semantic model says NOT_EQUIVALENT (saves two model calls per pair; measured NOT_EQUIVALENT
precision is 80-87% on independent sets, so those DIFFERENT verdicts are SUSPECTED, not proven, and `proven_by` says so).
The core calls no model: judges are callables supplied by the caller, exactly as in aixl.arbiter.decide."""
from dataclasses import dataclass, field
from aixl import arbiter
from aixl.semantic.compare import compare_texts
from aixl.semantic.model import Verdict


@dataclass
class HybridDecision:
    verdict: str                      # SAME | DIFFERENT | UNSURE | REVIEW
    proven_by: str                    # arbiter | arbiter+semantic | arbiter-dissent | semantic-suspect | none
    semantic: Verdict
    arbiter: object = None            # aixl.arbiter.Decision, or None when no judge was called
    notes: list = field(default_factory=list)

    @property
    def same(self) -> bool:
        return self.verdict == "SAME"

    def to_dict(self) -> dict:
        return dict(verdict=self.verdict, proven_by=self.proven_by, semantic=self.semantic.to_dict(), notes=self.notes,
                    arbiter=None if self.arbiter is None else dict(verdict=self.arbiter.verdict, ok=self.arbiter.ok, per_judge=self.arbiter.per_judge,
                                                                  from_memo=self.arbiter.from_memo, obfuscation=self.arbiter.obfuscation))


def decide(a: str, b: str, judges: dict | None = None, memo=None, short_circuit: bool = False, retries: int = 1) -> HybridDecision:
    sem = compare_texts(a, b)
    if sem.verdict == "NOT_EQUIVALENT" and (short_circuit or not judges):
        return HybridDecision("DIFFERENT", "semantic-suspect", sem, None,
                              ["semantic model found a definitive difference; measured precision of this verdict is 80-87% on independent sets, so it is SUSPECTED, not proven"])
    if not judges:
        return HybridDecision("UNSURE", "none", sem, None, ["no judges supplied: the semantic track alone never proves sameness"])
    d = arbiter.decide(a, b, judges, memo, retries)
    notes = []
    if d.verdict == "DIFFERENT":
        if sem.verdict == "EQUIVALENT": notes.append("the semantic model considered them equivalent but a judge dissented; dissent wins")
        return HybridDecision("DIFFERENT", "arbiter-dissent", sem, d, notes)
    if d.verdict == "SAME":
        if sem.verdict == "NOT_EQUIVALENT":
            return HybridDecision("REVIEW", "none", sem, d, ["both judges said SAME but the semantic model found a definitive difference: " +
                                                              "; ".join(f"{x.path} {x.type}" for x in sem.diffs[:3])])
        amb = [c for c in sem.flags if c.startswith("AMBIGUOUS")]
        if sem.verdict == "INCONCLUSIVE" and amb:
            return HybridDecision("REVIEW", "none", sem, d, ["both judges said SAME, but the semantic model flags the text as ambiguous (" + ", ".join(amb) +
                                                              "): sameness of an ambiguous instruction is a guess, not a proof"])
        return HybridDecision("SAME", "arbiter+semantic" if sem.verdict == "EQUIVALENT" else "arbiter", sem, d, notes)
    if sem.verdict == "NOT_EQUIVALENT": notes.append("the arbiter is unsure, and the semantic model suspects a difference")
    return HybridDecision("UNSURE", "none", sem, d, notes)
