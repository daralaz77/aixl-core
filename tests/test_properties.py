"""Property + invariant tests (master prompt §62-64). Run over a fixed ES/EN/PT corpus; `today` is pinned."""
import datetime

import pytest

from aixl.api import service as S
from aixl.core.comparator import compare_graphs
from aixl.core.fingerprint import fingerprint_graph
from aixl.serialization import aixl_codec, json_codec

TODAY = datetime.date(2026, 10, 2)
CORPUS = [
    "Envía el informe a Ana mañana.", "Send the report to Ana tomorrow.", "Envie o relatório para Ana amanhã.",
    "No envíes el informe.", "Do not send the report.", "Não envie o relatório.",
    "Envía el informe a Juan.", "Envía el informe en PDF.", "Busca hasta 10 resultados.",
    "Si el archivo existe, envíalo.", "Elimina los registros antiguos.", "Delete all the files.",
    "No envíes el documento fuera de la organización.", "Analiza las ventas del año pasado.",
    "Busca el informe más reciente y envíalo a Ana.", "Genera un resumen en JSON.",
    "Traduce el documento al inglés.", "Don't share the file with anyone.", "Exporta los datos a CSV.",
]


def g(t): return S.to_semantic(t)


@pytest.mark.parametrize("t", CORPUS)
def test_canonical_is_deterministic(t):
    assert g(t).canonical(today=TODAY) == g(t).canonical(today=TODAY)


@pytest.mark.parametrize("t", CORPUS)
def test_canonicalize_idempotent_via_roundtrip(t):
    """canonical(decode(encode(g))) == canonical(g): the canonical form is a fixed point of the codec."""
    a = g(t)
    b = aixl_codec.decode(aixl_codec.encode(a))
    assert a.canonical(today=TODAY) == b.canonical(today=TODAY), t


@pytest.mark.parametrize("t", CORPUS)
def test_json_serialize_deserialize_preserves_structure(t):
    a = g(t)
    b = json_codec.loads(json_codec.dumps(a))
    assert a.to_dict() == b.to_dict()
    assert a.canonical(today=TODAY) == b.canonical(today=TODAY)


@pytest.mark.parametrize("t", CORPUS)
def test_fingerprint_matches_after_roundtrips(t):
    a = g(t)
    fa = fingerprint_graph(a, today=TODAY)
    assert fa == fingerprint_graph(json_codec.loads(json_codec.dumps(a)), today=TODAY)
    assert fa == fingerprint_graph(aixl_codec.decode(aixl_codec.encode(a)), today=TODAY)


@pytest.mark.parametrize("t", CORPUS)
def test_self_comparison_is_equivalent(t):
    assert compare_graphs(g(t), g(t), today=TODAY).equivalent


# ---- invariants §63 / security §64 ----
def _neg(t): return g(t).canonical(today=TODAY)["negation"]

@pytest.mark.parametrize("pos,neg", [("Envía el informe.", "No envíes el informe."),
                                     ("Send the report.", "Do not send the report."),
                                     ("Envie o relatório.", "Não envie o relatório.")])
def test_negation_must_not_disappear(pos, neg):
    assert not _neg(pos) and _neg(neg)
    assert not S.compare(pos, neg).equivalent
    assert fingerprint_graph(g(pos), today=TODAY) != fingerprint_graph(g(neg), today=TODAY)
    assert S.detect_drift(neg, pos).drift


@pytest.mark.parametrize("a,b", [("Envía el informe a Ana.", "Envía el informe a Carlos."),
                                 ("Send the report to Ana.", "Send the report to Carlos.")])
def test_target_must_not_change_silently(a, b):
    assert not S.compare(a, b).equivalent
    assert S.detect_drift(a, b).drift


@pytest.mark.parametrize("a,b", [("Busca hasta 10 resultados.", "Busca resultados."),
                                 ("Si el archivo existe, envíalo.", "Envía el archivo."),
                                 ("No envíes el documento fuera de la organización.", "Envía el documento.")])
def test_constraint_and_condition_loss_is_drift(a, b):
    assert S.detect_drift(a, b).drift


def test_time_must_not_be_invented():
    c = g("Envía el informe.").canonical(today=TODAY)
    assert c["time"] == () and "ANA" not in c["entities"]
    assert not S.compare("Envía el informe.", "Envía el informe mañana.").equivalent


def test_unknown_must_not_become_known():
    c = g("Envía el informe.").canonical(today=TODAY)
    assert c["time"] == () and c["location"] == () and c["quantities"] == () and c["output"] == ()


def test_no_execution_layer_imported():
    import aixl.core.semantic_graph as m
    src = open(m.__file__).read()
    assert "subprocess" not in src and "os.system" not in src


def test_cross_lingual_convergence():
    fs = {fingerprint_graph(g(t), today=TODAY) for t in CORPUS[:3]}
    assert len(fs) == 1
