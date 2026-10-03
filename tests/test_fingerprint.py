import datetime
import pytest
from aixl import semantic_fingerprint as fp, semantic_fingerprint_aixl as fpa, to_aixl

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
