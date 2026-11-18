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


def test_prepare_offers_a_short_circuit_only_for_a_definite_difference():
    from aixl.hybrid_protocol import prepare
    assert prepare(*DEFINITE)["short_circuit"]["available"] is True
    assert prepare("Keep at least 5 backups.", "Keep 5 or more backups.")["short_circuit"]["available"] is False


def test_the_mcp_tool_accepts_the_veto_argument():
    import inspect

    from aixl import mcp_server
    assert "veto" in inspect.signature(mcp_server.aixl_hybrid_decide).parameters
