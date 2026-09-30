import pytest
from aixl.translators.natural_to_semantic import to_graph


def c(text):
    return to_graph(text).canonical()


def test_paraphrase_converges_to_same_canonical_form():
    a = c("Analiza las ventas del primer trimestre de 2026.")
    b = c("Examina las ventas de Q1 2026.")
    assert a == b
    assert a["actions"] == ("ANALYZE",) and a["data"] == ("SALES",) and a["time"] == ("Q1-2026",)


def test_language_independent():
    assert c("Analyze sales.") == c("Analiza las ventas.") == c("Analise as vendas.")


def test_do_not_invent_missing_information():
    x = c("Analiza las ventas.")
    assert x["time"] == () and x["location"] == () and x["output"] == () and x["quantities"] == () and x["constraints"] == ()


def test_negation_prohibition_and_permission_modalities():
    assert c("No elimines el reporte.")["negation"] == ("FORBID:DELETE",)
    assert c("Prohíbe eliminar el reporte.")["negation"] == ("FORBID:DELETE",)
    assert c("Está prohibido eliminar el reporte.")["negation"] == ("FORBID:DELETE",)
    assert c("Permite eliminar el reporte.")["negation"] == ("ALLOW:DELETE",)
    assert c("Elimina el reporte.")["negation"] == ()


def test_quantities_are_explicit_and_normalized():
    assert c("Analiza 100 registros.")["quantities"] == ("100:RECORDS",)
    assert c("Analiza 1.000 registros.")["quantities"] == ("1000:RECORDS",)
    assert c("Analyze 1,000 records.")["quantities"] == ("1000:RECORDS",)
    assert c("Analiza 100 registros.") != c("Analiza 1000 registros.")


def test_dates_refs_and_confidence_are_not_taken_for_quantities():
    x = c("Analiza el reporte #77 de 2026-03-15 con confianza >= 0.90, máximo 20.")
    assert x["quantities"] == () and x["references"] == ("#77",) and x["time"] == ("2026-03-15",)
    assert x["modifiers"] == ("CONFIDENCE>=0.9",)


def test_count_condition_is_preserved():
    x = c("Analiza las ventas si existen más de 100 registros.")
    assert x["conditions"] == ("COUNT>100:RECORDS",)
    assert x["conditions"] != c("Analiza las ventas.")["conditions"]


def test_output_formats_and_visibility():
    assert c("Genera un informe en PDF.")["output"] == ("PDF",)
    assert c("Genera un informe en JSON.")["output"] == ("JSON",)
    assert ("VISIBILITY=PUBLIC",) == c("Envía el reporte público.")["constraints"]


def test_extension_actions():
    x = c("Activa la alerta y desactiva el reporte.")
    assert x["actions"] == ("ENABLE", "DISABLE")
    assert c("Incluye los usuarios.")["actions"] == ("INCLUDE",)
    # design change after blind run 1: "excluye X" is canonically "no incluyas X" (graph keeps the surface action EXCLUDE)
    assert c("Excluye los usuarios.")["actions"] == ("INCLUDE",) and c("Excluye los usuarios.")["negation"] == ("FORBID:INCLUDE",)
    assert to_graph("Excluye los usuarios.").by_type("ACTION")[0].value == "EXCLUDE"
    assert c("Actualiza el reporte.")["actions"] == ("UPDATE",)


def test_aggregate_qualifier_keeps_meaning_different():
    assert c("Analiza las ventas.") != c("Analiza el total de ventas.")
    assert c("Analiza el total de ventas.")["data"] == ("TOTAL(SALES)",)


def test_before_after_constraints():
    assert "BEFORE=2026-03-15" in c("Analiza los reportes antes de 2026-03-15.")["constraints"]
    assert "AFTER=2026-03-15" in c("Analiza los reportes después de 2026-03-15.")["constraints"]
