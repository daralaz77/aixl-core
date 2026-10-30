"""compare_verified + aixl.logic: OFF by default (decision 2026-10-30); when turned on with {"logic": True} the engine can ADD a proof, never override a reliable verdict, and any disagreement is INCONCLUSIVE."""
ON = {"logic": True}
import pytest

from aixl.api import service
from aixl.api.service import compare_verified

A = "It is not true that we ship and we invoice."          # De Morgan: the comparator does not prove it, the logic engine does
B = "We do not ship or we do not invoice."


def test_a_logic_proof_upgrades_an_unproven_pair():
    d = compare_verified(A, B, ON)
    assert d["verdict"] == "EQUIVALENT" and d["equivalent"] and d["verified"] and d["proof"] == "logic"
    assert d["logic"]["verdict"] == "EQUIVALENT_LOGIC" and d["raw_verdict"] in ("INCONCLUSIVE", "NOT_EQUIVALENT")


def test_off_by_default_the_published_behaviour_does_not_change():
    for cfg in (None, {}, {"logic": False}):
        d = compare_verified(A, B, cfg)
        assert d["verdict"] != "EQUIVALENT" and "logic" not in d and "proof" not in d


def test_default_equals_the_core_result():
    from aixl.api.service import _compare_verified_core
    for a, b in ((A, B), ("Notify Ana unless the ticket is closed.", "Notify Ana if the ticket is not closed."), ("Elimina el reporte.", "No elimines el reporte.")):
        assert compare_verified(a, b) == _compare_verified_core(a, b)


def test_a_pair_the_comparator_already_proves_is_left_alone():
    d = compare_verified("Send the report if the client approves.", "If the client approves, send the report.", ON)
    assert d["verdict"] == "EQUIVALENT" and "proof" not in d and d["logic"]["verdict"] == "EQUIVALENT_LOGIC"


def test_a_real_conflict_unless_vs_if_not_is_inconclusive_not_a_guess():
    """the comparator reliably calls `unless` and `if ... not` different; the engine proves them equal: neither is trusted over the other."""
    d = compare_verified("Notify Ana unless the ticket is closed.", "Notify Ana if the ticket is not closed.", ON)
    assert d["verdict"] == "INCONCLUSIVE" and d["logic_conflict"] is True and d["equivalent"] is False and d["raw_verdict"] == "NOT_EQUIVALENT"


def test_a_logic_counterexample_is_a_reliable_difference():
    d = compare_verified("Send the report if the client approves.", "Send the report only if the client approves.", ON)
    assert d["verdict"] == "NOT_EQUIVALENT" and d["equivalent"] is False and d["difference_reliable"] is True
    assert d["logic"]["verdict"] == "DIFFERENT_LOGIC" and d["logic"]["counterexample"]


def test_abstention_changes_nothing_but_adds_the_key():
    a, b = "Send the report to Ana if the client approves.", "Send the report to Luis if the client approves."
    on, off = compare_verified(a, b, ON), compare_verified(a, b, {"logic": False})
    assert on["logic"]["verdict"] == "ABSTAIN"
    assert {k: v for k, v in on.items() if k != "logic"} == off


def test_keys_of_the_core_result_are_preserved():
    on, off = compare_verified(A, B, ON), compare_verified(A, B, {"logic": False})
    assert set(off) <= set(on) | {"difference_reliable"} and {"verdict", "equivalent", "verified", "complete"} <= set(on)


def _fake_logic(verdict):
    return lambda a, b: {"verdict": verdict, "reason": "fake", "counterexample": {"x": True}, "formula_a": "a", "formula_b": "b"}


def test_conflict_equivalent_logic_vs_a_reliable_difference_is_inconclusive(monkeypatch):
    import aixl.logic as L
    monkeypatch.setattr(L, "logic_compare", _fake_logic("EQUIVALENT_LOGIC"))
    base = {"verdict": "NOT_EQUIVALENT", "equivalent": False, "verified": True, "difference_reliable": True}
    d = service._apply_logic("x", "y", dict(base))
    assert d["verdict"] == "INCONCLUSIVE" and d["logic_conflict"] is True and d["equivalent"] is False and d["raw_verdict"] == "NOT_EQUIVALENT"


def test_conflict_comparator_proof_vs_logic_counterexample_is_inconclusive(monkeypatch):
    import aixl.logic as L
    monkeypatch.setattr(L, "logic_compare", _fake_logic("DIFFERENT_LOGIC"))
    d = service._apply_logic("x", "y", {"verdict": "EQUIVALENT", "equivalent": True, "verified": True})
    assert d["verdict"] == "INCONCLUSIVE" and d["logic_conflict"] is True and d["equivalent"] is False and d["verified"] is False


def test_a_proof_by_the_comparator_is_kept_when_the_engine_agrees(monkeypatch):
    import aixl.logic as L
    monkeypatch.setattr(L, "logic_compare", _fake_logic("EQUIVALENT_LOGIC"))
    d = service._apply_logic("x", "y", {"verdict": "EQUIVALENT", "equivalent": True, "verified": True})
    assert d["verdict"] == "EQUIVALENT" and "proof" not in d


def test_a_crash_in_the_logic_layer_never_changes_the_verdict(monkeypatch):
    import aixl.logic as L
    def boom(a, b):
        raise RuntimeError("bug")
    monkeypatch.setattr(L, "logic_compare", boom)
    on, off = compare_verified("Elimina el reporte.", "No elimines el reporte.", ON), compare_verified("Elimina el reporte.", "No elimines el reporte.", {"logic": False})
    assert on["verdict"] == off["verdict"] and on["logic"]["verdict"] == "ABSTAIN"


@pytest.mark.parametrize("a,b", [("Do not delete the file and do not delete the backup.", "Delete the file and delete the backup."),
                                 ("Fetch top 10 sales records and generate a JSON file.", "Generate a JSON file and fetch top 10 sales records.")])
def test_never_a_false_equivalent_on_known_traps(a, b):
    assert compare_verified(a, b, ON)["verdict"] != "EQUIVALENT"
