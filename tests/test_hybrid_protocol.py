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


# Strict hybrid (2026-11-06): measured on blind19-26, the default hybrid let through about 5-6% of non-equivalent pairs because two LLM judges err together;
# `strict=True` also needs the rule-based comparator to PROVE equivalence, otherwise REVIEW (a person decides).
SAME2 = {"j1": "SAME", "j2": "SAME"}
UNPROVEN = ("Get the contract signed by Friday.", "Make sure the contract is signed by Friday.")        # blind26 R008: judges say SAME, comparator INCONCLUSIVE


def test_strict_sends_a_unanimous_same_to_review_when_the_comparator_cannot_prove_it():
    assert hp.decide(*UNPROVEN, SAME2)["verdict"] == "SAME"                       # default behaviour unchanged
    r = hp.decide(*UNPROVEN, SAME2, strict=True)
    assert r["verdict"] == "REVIEW" and r["strict"] is True and "did not prove EQUIVALENT" in " ".join(r["notes"])


def test_strict_keeps_same_when_the_comparator_proves_equivalent():
    r = hp.decide(A, B, SAME2, strict=True)
    assert r["verdict"] == "SAME" and r["proven_by"] == "arbiter+semantic"


@pytest.mark.parametrize("strict", [False, True])
def test_strict_never_loosens_anything(strict):
    assert hp.decide(A, B, {"j1": "SAME", "j2": "DIFFERENT"}, strict=strict)["verdict"] == "DIFFERENT"
    assert hp.decide(A, B, {"j1": "SAME"}, strict=strict)["verdict"] != "SAME"
    assert hp.decide("Delete all files except the logs", "Delete all files", SAME2, strict=strict)["verdict"] == "REVIEW"


def test_default_is_not_strict():
    assert hp.decide(A, B, SAME2)["strict"] is False


@pytest.mark.parametrize("a,b", [UNPROVEN,
                                 ("Get the design team to update the logo on the website.", "Have the designers change the website logo."),          # blind26 S008
                                 ("If the primary API is down, use the backup one.", "If the main API doesn't respond, switch to the backup.")])  # blind26 S040
def test_the_three_blind26_judge_false_sames_do_not_pass_strict(a, b):
    assert hp.decide(a, b, SAME2, strict=True)["verdict"] != "SAME"
