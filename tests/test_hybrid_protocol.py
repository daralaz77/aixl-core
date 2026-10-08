"""Two-step hybrid protocol (aixl/hybrid_protocol.py): the core combines judge verdicts supplied by the caller; it calls no model."""
import json

import pytest

from aixl import arbiter
from aixl import hybrid_protocol as hp

A, B = "Generate the sales report", "Create the sales report"


def test_prepare_gives_versioned_rules_and_exact_judge_input_without_calling_any_model():
    p = hp.prepare(A, B)
    assert p["rules_id"] == arbiter.rules_id() and p["judge_system_prompt"] == arbiter.rules_text()
    assert json.loads(p["judge_input"]) == {"id": "pair", "a": A, "b": B}
    assert p["semantic"]["verdict"] in {"EQUIVALENT", "NOT_EQUIVALENT", "INCONCLUSIVE"} and p["protocol"]


def test_two_judges_same_and_no_veto_is_same():
    r = hp.decide(A, B, {"j1": "SAME", "j2": "SAME"})
    assert r["verdict"] == "SAME" and r["action"] == hp.ACTION["SAME"] and r["rules_id"] == arbiter.rules_id()


def test_any_dissent_blocks_sameness():
    assert hp.decide(A, B, {"j1": "SAME", "j2": "DIFFERENT"})["verdict"] == "DIFFERENT"


@pytest.mark.parametrize("verdicts", [{}, {"j1": "SAME"}, {"j1": "SAME", "j2": "maybe"}, {"j1": "SAME", "j2": None}, {"j1": "SAME", "j2": ""}])
def test_fewer_than_two_valid_judges_never_produce_same(verdicts):
    r = hp.decide(A, B, verdicts)
    assert r["verdict"] != "SAME"


def test_semantic_veto_turns_a_unanimous_same_into_review():
    r = hp.decide("Delete all files except the logs", "Delete all files", {"j1": "SAME", "j2": "SAME"})
    assert r["verdict"] == "REVIEW" and r["action"] == hp.ACTION["REVIEW"] and "except" in " ".join(r["notes"])


def test_bad_judge_input_never_raises():
    hp.decide(A, B, None)
    hp.decide(A, B, {1: 5, "x": ["SAME"]})
