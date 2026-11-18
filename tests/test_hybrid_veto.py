import pytest

from aixl.hybrid_protocol import decide
from aixl.semantic.hybrid import decide as hybrid_decide

SAME2 = {"j1": "SAME", "j2": "SAME"}
AMBIGUOUS = ("Do not merge the branch until all tests pass.", "The branch may be merged only after every test has passed.")     # INCONCLUSIVE + AMBIGUOUS_NEGATED_TEMPORAL
DEFINITE = ("Keep at least 5 backups.", "Keep at most 5 backups.")                                                               # NOT_EQUIVALENT


def test_default_veto_sends_an_ambiguous_same_to_review():
    assert decide(*AMBIGUOUS, SAME2)["verdict"] == "REVIEW"


def test_definite_veto_lets_an_ambiguity_flag_through():
    out = decide(*AMBIGUOUS, SAME2, veto="definite")
    assert out["verdict"] == "SAME" and out["veto"] == "definite"


def test_definite_veto_still_stops_a_definite_difference():
    assert decide(*DEFINITE, SAME2, veto="definite")["verdict"] == "REVIEW"


def test_one_dissenting_judge_still_wins_under_definite():
    assert decide(*AMBIGUOUS, {"j1": "SAME", "j2": "DIFFERENT"}, veto="definite")["verdict"] == "DIFFERENT"


def test_an_unknown_veto_value_is_refused():
    with pytest.raises(ValueError):
        hybrid_decide(*AMBIGUOUS, {"j1": lambda a, b: "SAME"}, veto="none")
