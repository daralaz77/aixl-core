"""Published comparison surface (consejo-5x audit 2026-10-13): never EQUIVALENT without proof; AND<->OR flips are not invisible any more."""
import pytest

import aixl
from aixl.core.connectives import disjunction_differs, or_count
from aixl.envelope import seal, verify


def test_known_closed_lexicon_limits_become_inconclusive_with_the_reason():
    # (2026-10-13: `... and list the differences` was the old example; the core now sees the extra clause, so a changed UNKNOWN word is the limit)
    a, b = "Delete the notes about the quarterly handover.", "Delete the notes about the quarterly handxyz."
    d = aixl.compare_verified(a, b)
    assert aixl.compare(a, b).equivalent                      # the core still says so (documented limit)
    assert d["verdict"] == "INCONCLUSIVE" and d["equivalent"] is False and d["verified"] is False and d["raw_verdict"] == "EQUIVALENT"
    assert "handover" in d["unaccounted"]["a"] and "handxyz" in d["unaccounted"]["b"]


def test_verified_keeps_every_key_of_compare_and_a_true_paraphrase():
    d = aixl.compare_verified("Analiza las ventas de Q1 2026.", "Analyze Q1 2026 sales.")
    assert d["equivalent"] is True and d["verified"] is True
    assert set(aixl.compare("Analiza las ventas de Q1 2026.", "Analyze Q1 2026 sales.").to_dict()) <= set(d)


def test_negative_verdicts_are_untouched():
    d = aixl.compare_verified("Elimina el reporte.", "No elimines el reporte.")
    assert d["equivalent"] is False and d["verdict"] == "NOT_EQUIVALENT" and "raw_verdict" not in d


@pytest.mark.parametrize("a,b", [("Envía el informe a Ana y a Luis.", "Envía el informe a Ana o a Luis."),
                                 ("Send the report to Ana and notify Luis.", "Send the report to Ana or notify Luis."),
                                 ("Envie o relatório para Maria e João.", "Envie o relatório para Maria ou João.")])
def test_and_or_flip_is_caught_by_every_shipped_layer(a, b):
    assert disjunction_differs(a, b)
    assert aixl.compare_verified(a, b)["equivalent"] is False
    assert verify(seal(a), b) != "MATCH"                      # was MATCH for the first two before the connective witness


def test_or_count_basics():
    assert or_count("a Ana y a Luis") == 0 and or_count("a Ana o a Luis") == 1 and or_count("Ana or Luis OU Maria") == 2
    assert not disjunction_differs("ventas y clientes", "ventas e clientes")        # and-vs-and spelling is not a disjunction change


def test_oversized_input_is_unverified_not_an_exception():
    d = aixl.compare_verified("x " * 20000, "y")
    assert d["verdict"] == "UNVERIFIED" and d["equivalent"] is False and d["reason"] == "input_too_large"


def test_mcp_and_a2a_surfaces_use_the_verified_comparison():
    import inspect

    import aixl.agents.a2a_server as A2A
    import aixl.mcp_server as M
    assert "compare_verified" in inspect.getsource(M.aixl_compare)
    assert "compare_verified" in inspect.getsource(A2A)
