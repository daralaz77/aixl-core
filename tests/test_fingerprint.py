import datetime

import pytest

from aixl import semantic_fingerprint as fp
from aixl import semantic_fingerprint_aixl as fpa
from aixl import to_aixl

D = datetime.date(2026, 10, 2)


def f(t):
    return fp(t, today=D)


def test_paraphrase_same_fingerprint():
    assert f("Analiza las ventas del primer trimestre de 2026.") == f("Examina las ventas de Q1 2026.")


def test_cross_lingual_same_fingerprint():
    es = f("Analiza las ventas de Q1 2026.")
    assert es == f("Analyze the sales of Q1 2026.") == f("Analise as vendas do Q1 2026.")


def test_punctuation_case_whitespace_ignored():
    assert f("analiza las ventas de Q1 2026") == f("  Analiza   las ventas de Q1 2026!! ")


def test_deterministic_and_stable_format():
    a = f("Analiza las ventas de Q1 2026.")
    assert a == f("Analiza las ventas de Q1 2026.") and len(a) == 16 and int(a, 16) >= 0


@pytest.mark.parametrize("a,b", [
    ("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026."),
    ("Analiza las ventas de Q1 2026.", "No analices las ventas de Q1 2026."),
    ("Analyze the sales of Q1 2026.", "Analyze the costs of Q1 2026."),
])
def test_real_differences_change_fingerprint(a, b):
    assert f(a) != f(b)


def test_aixl_roundtrip_same_fingerprint():
    t = "Analiza las ventas de Q1 2026."
    assert fpa(to_aixl(t), today=D) == f(t)


def test_fingerprint_of_a_graph_without_residue_is_the_0_4_0_value():
    """Adding the `residue` dimension (0.5) must not change any fingerprint stored under 0.4.0: an empty residue is omitted from canonical()."""
    import datetime

    from aixl import from_aixl, semantic_fingerprint
    assert semantic_fingerprint("Envía el informe a Ana en PDF.", today=datetime.date(2026, 10, 3)) == "4d601cd77a368a82"
    g = from_aixl('V:AIXL-0.3 I:REQUEST_EXECUTION A:SEND E:REPORT Y:@ANA O:PDF R:"every week"')
    assert "residue" in g.canonical() and "residue" not in from_aixl("V:AIXL-0.3 I:REQUEST_EXECUTION A:SEND E:REPORT").canonical()
