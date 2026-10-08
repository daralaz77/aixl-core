import pytest

from aixl.serialization import aixl_codec, json_codec
from aixl.serialization.aixl_codec import AixlError
from aixl.translators.natural_to_semantic import to_graph

SAMPLES = [
    "Analiza las ventas del primer trimestre de 2026", "No elimines el reporte #81.", "Analiza 1.000 registros.",
    "Analiza las ventas si existen más de 100 registros.", "Genera un informe en PDF.", "Envía el reporte público.",
    "Compara el dataset #77 con el dataset #81 en JSON.", "Analiza el total de ventas de Q2 2026 con confianza >= 0.90.",
    "Prohíbe eliminar el reporte.", "Activa la alerta.", "Traduce el reporte al francés y al alemán, máximo 3.",
    "Verifica el resultado si la confianza es menor a 0.80.", "Analiza los reportes antes de 2026-03-15.",
]


@pytest.mark.parametrize("text", SAMPLES)
def test_roundtrip_preserves_canonical_form(text):
    g = to_graph(text)
    back = aixl_codec.decode(aixl_codec.encode(g))
    assert back.canonical() == g.canonical(), (aixl_codec.encode(g), g.canonical(), back.canonical())


def test_aixl_example_from_master_prompt():
    a = aixl_codec.encode(to_graph("Analiza las ventas del primer trimestre de 2026"))
    assert a == "V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES T:Q1-2026"


def test_json_roundtrip_and_canonical_json_is_stable():
    g = to_graph("Analiza 100 registros de ventas en CSV.")
    assert json_codec.loads(json_codec.dumps(g)).canonical() == g.canonical()
    assert json_codec.canonical_json(g) == json_codec.canonical_json(to_graph("Analyze 100 records of sales as CSV."))


def test_invalid_aixl_is_rejected_not_guessed():
    for bad in ["", "hello", "V:AIXL-0.3 Z:X", "V:AIXL-9.9 A:ANALYZE"]:
        with pytest.raises(AixlError):
            aixl_codec.decode(bad)


def test_aixl_is_a_serialization_not_the_core():
    g = to_graph("No elimines el reporte.")
    assert "nodes" in g.to_dict() and aixl_codec.encode(g).startswith("V:AIXL-0.3")
