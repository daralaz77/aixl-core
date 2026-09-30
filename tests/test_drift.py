from aixl.translators.natural_to_semantic import to_graph
from aixl.core.drift import detect_drift_graphs
from aixl.core.ontology import load_config
import copy


def d(a, b, cfg=None):
    return detect_drift_graphs(to_graph(a), to_graph(b), cfg)


def test_no_drift_for_paraphrase():
    assert d("Analiza las ventas de Q1 2026.", "Examina las ventas del primer trimestre de 2026.").level == "NO_DRIFT"


def test_time_drift_is_reported_with_concrete_difference():
    r = d("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026.")
    assert r.level == "MAJOR_DRIFT" and r.differences[0].field == "TIME"


def test_critical_pairs():
    assert d("Elimina el reporte.", "No elimines el reporte.").critical
    assert d("Permite eliminar el reporte.", "Prohíbe eliminar el reporte.").critical
    assert d("Analiza 100 registros.", "Analiza 1000 registros.").critical
    assert d("Haz público el reporte.", "Haz privado el reporte.").critical
    assert d("Activa la alerta.", "Desactiva la alerta.").critical
    assert d("Envía el reporte.", "No envíes el reporte.").critical
    assert d("Analiza los reportes antes de 2026-03-15.", "Analiza los reportes después de 2026-03-15.").critical


def test_severity_is_configurable_not_hardcoded():
    cfg = copy.deepcopy(load_config())
    cfg["severity"]["time"] = "CRITICAL"
    assert d("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026.", cfg).level == "CRITICAL_DRIFT"
    cfg["severity"]["time"] = "MINOR"
    assert d("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026.", cfg).level == "MINOR_DRIFT"


def test_report_serializes_with_explanation():
    r = d("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026.").to_dict()
    assert r["differences"][0]["source"] == "Q1-2026" and r["explanation"]
