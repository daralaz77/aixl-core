"""validate() §43-44, round_trip() §38, provenance §68 — added 2026-10-02."""
import pytest
from aixl.api import service as S
from aixl.core.semantic_graph import SemanticGraph
from aixl.core.semantic_object import SemanticObject
from aixl.core.semantic_relation import SemanticRelation
from aixl.core.validator import validate_graph
from aixl.serialization import json_codec
from tests.test_properties import CORPUS


def codes(r): return {i.code for i in r.issues}


# ---- validate ----
@pytest.mark.parametrize("t", CORPUS)
def test_corpus_is_never_invalid(t):
    assert S.validate(t).status in ("VALID", "VALID_WITH_WARNINGS")


def test_clean_text_is_valid():
    assert S.validate("Envía el informe a Ana mañana.").status == "VALID"


def test_loss_is_reported_as_warning_not_hidden():
    r = S.validate("Don't share the file with anyone.")
    assert r.status == "VALID_WITH_WARNINGS" and "SEMANTIC_LOSS" in codes(r)


def test_contradictory_modalities_invalid():
    g = SemanticGraph()
    g.add_node("ACTION", "SEND", {"modality": "REQUEST", "order": 0})
    g.add_node("ACTION", "SEND", {"modality": "FORBID", "order": 1})
    r = validate_graph(g)
    assert r.status == "INVALID" and "CONTRADICTION" in codes(r)


def test_structural_errors_are_structured():
    g = SemanticGraph([SemanticObject("a", "BOGUS", ""), SemanticObject("a", "QUANTITY", "many", confidence=2.0),
                       SemanticObject("t", "TIME", "2026-02-30")],
                      [SemanticRelation("a", "TARGET", "ghost")])
    r = validate_graph(g)
    assert r.status == "INVALID"
    assert {"UNKNOWN_TYPE", "MISSING_REQUIRED_FIELD", "INVALID_SCHEMA", "INVALID_QUANTITY", "INVALID_TIME", "INVALID_RELATION"} <= codes(r)
    assert all(i.code != "ERROR" and i.message for i in r.issues)


def test_validate_does_not_mutate():
    g = S.to_semantic("Envía el informe a Ana.")
    before = g.to_dict()
    validate_graph(g)
    assert g.to_dict() == before


# ---- round_trip ----
@pytest.mark.parametrize("t", CORPUS)
def test_round_trip_preserves_corpus(t):
    r = S.round_trip(t)
    assert r.preserved and r.fidelity == 1.0 and r.aixl.startswith("V:AIXL-0.3")


def test_round_trip_reports_codec_failure_as_loss():
    class Boom(SemanticGraph):
        def to_frame(self): raise ValueError("cannot encode")
    r = S.round_trip(Boom())
    assert not r.preserved and r.fidelity == 0.0 and "cannot encode" in r.error


# ---- provenance ----
def test_derived_nodes_are_inferred_stated_are_explicit():
    g = S.to_semantic("Envía el informe a Ana.")
    prov = {n.type: n.provenance for n in g.nodes}
    assert prov["ACTION"] == "EXPLICIT" and prov["ENTITY"] == "EXPLICIT"
    assert prov["INTENT"] == "INFERRED"
    g2 = S.to_semantic("Analiza las ventas.")
    assert {n.provenance for n in g2.nodes if n.type == "GOAL"} <= {"INFERRED"}


def test_provenance_survives_json_and_does_not_affect_canonical():
    g = S.to_semantic("Envía el informe a Ana.")
    h = json_codec.loads(json_codec.dumps(g))
    assert [n.provenance for n in h.nodes] == [n.provenance for n in g.nodes]
    for n in h.nodes:
        n.provenance = "MODEL_DERIVED"
    assert h.canonical() == g.canonical()


def test_mark_model_derived_keeps_inferred():
    g = S.to_semantic("Envía el informe a Ana.").mark_model_derived("llm")
    assert {n.provenance for n in g.nodes if n.type == "ACTION"} == {"MODEL_DERIVED"}
    assert {n.provenance for n in g.nodes if n.type == "INTENT"} == {"INFERRED"}
    assert all(n.source == "llm" for n in g.nodes)
