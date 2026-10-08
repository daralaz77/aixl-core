from aixl.core.contradiction import detect_contradiction_graphs
from aixl.translators.natural_to_semantic import to_graph


def con(a, b):
    return detect_contradiction_graphs(to_graph(a), to_graph(b))


def test_delete_vs_forbid_delete():
    r = con("Elimina el reporte #4.", "No elimines el reporte #4.")
    assert r.contradiction and r.alerts[0].type == "DELETE_VS_FORBID_DELETE"


def test_enable_vs_disable_and_include_vs_exclude():
    assert con("Activa la alerta.", "Desactiva la alerta.").contradiction
    assert con("Incluye los usuarios en el reporte.", "Excluye los usuarios del reporte.").contradiction


def test_allow_vs_forbid():
    r = con("Permite eliminar el reporte.", "Prohíbe eliminar el reporte.")
    assert r.contradiction and r.alerts[0].type == "ALLOW_VS_FORBID"


def test_public_vs_private_and_before_vs_after():
    assert con("Haz público el reporte #3.", "Haz privado el reporte #3.").contradiction
    assert con("Analiza los reportes antes de 2026-03-15.", "Analiza los reportes después de 2026-03-15.").contradiction


def test_different_texts_are_not_contradictions():
    assert not con("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026.").contradiction
    assert not con("Elimina el reporte #4.", "No elimines el reporte #5.").contradiction      # different objects
    assert not con("Genera un informe en PDF.", "Genera un informe en JSON.").contradiction
    assert not con("Analiza las ventas.", "Analiza las ventas de Q1 2026.").contradiction     # refinement, compatible


def test_same_direction_is_not_contradiction():
    assert not con("No elimines el reporte.", "Prohíbe eliminar el reporte.").contradiction
