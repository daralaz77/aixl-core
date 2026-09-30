import pytest
from aixl.translators.natural_to_semantic import to_graph
from aixl.core.comparator import compare_graphs, format_diff


def cmp(a, b):
    return compare_graphs(to_graph(a), to_graph(b))


def fields(r):
    return {d.field for d in r.differences}


def test_demo1_paraphrase_is_equivalent():
    r = cmp("Analiza las ventas del primer trimestre de 2026.", "Examina las ventas de Q1 2026.")
    assert r.equivalent and r.similarity == 1.0 and r.differences == [] and r.critical_changes == []


def test_demo2_period_change():
    r = cmp("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026.")
    assert not r.equivalent and fields(r) == {"TIME"}
    d = r.differences[0]
    assert (d.source, d.target) == ("Q1-2026", "Q2-2026")


def test_demo3_negation_is_critical():
    r = cmp("Elimina el reporte.", "No elimines el reporte.")
    assert not r.equivalent and "NEGATION" in fields(r) and r.drift_level == "CRITICAL_DRIFT" and r.critical_changes


def test_demo4_quantity():
    r = cmp("Analiza 100 registros.", "Analiza 1000 registros.")
    assert not r.equivalent and fields(r) == {"QUANTITY"} and r.drift_level == "CRITICAL_DRIFT"
    assert cmp("Analiza 1.000 registros.", "Analiza 1000 registros.").equivalent


def test_demo5_confidence_constraint():
    r = cmp("Confianza >= 0.90", "Confianza >= 0.70")
    assert not r.equivalent and "MODIFIERS" in fields(r)
    assert cmp("Confianza >= 0.90", "Confianza >= .9").equivalent


def test_different_action_is_not_equivalent():
    r = cmp("Analiza las ventas.", "Elimina las ventas.")
    assert not r.equivalent and "ACTION" in fields(r)


def test_output_format_matters():
    r = cmp("Genera un informe en PDF.", "Genera un informe en JSON.")
    assert not r.equivalent and fields(r) == {"OUTPUT"}


def test_condition_removed_is_different():
    r = cmp("Analiza las ventas si existen más de 100 registros.", "Analiza las ventas.")
    assert not r.equivalent and "CONDITIONS" in fields(r)
    assert cmp("Analiza las ventas si existen más de 100 registros.", "Analyze sales if there are more than 100 records.").equivalent


def test_references_matter():
    assert not cmp("Compara el dataset #77 con el dataset #81.", "Compara el dataset #77 con el dataset #82.").equivalent


def test_aggregate_qualifier_is_not_assumed_equivalent():
    assert not cmp("Analiza las ventas.", "Analiza el volumen de ventas.").equivalent


def test_similar_words_different_meaning_are_separated():
    assert not cmp("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q1 2025.").equivalent


def test_score_is_bounded_and_graded():
    same = cmp("Analiza las ventas.", "Examina las ventas.")
    near = cmp("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026.")
    far = cmp("Analiza las ventas.", "Elimina los usuarios.")
    assert 0.0 <= far.similarity < near.similarity < same.similarity <= 1.0


def test_diff_text_is_human_readable():
    a, b = to_graph("Analiza las ventas de Q1 2026."), to_graph("Analiza las ventas de Q2 2026.")
    text = format_diff(a, b)
    assert "TIME" in text and "Q1-2026" in text and "Q2-2026" in text and "SEMANTIC DRIFT DETECTED" in text
    assert "No meaningful differences" in format_diff(a, a)
