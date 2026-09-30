import pytest
from aixl.core.semantic_object import SemanticObject
from aixl.core.semantic_relation import SemanticRelation
from aixl.core.semantic_graph import SemanticGraph
from aixl.core.ontology import type_of, load_config, ACTIONS
from aixl.legacy02.core.semantic_frame import SemanticFrame


def test_object_roundtrip_dict():
    o = SemanticObject("action_1", "ACTION", "ANALYZE", {"modality": "REQUEST"}, 0.98)
    assert SemanticObject.from_dict(o.to_dict()) == o


def test_relation_rejects_unknown_type():
    with pytest.raises(ValueError):
        SemanticRelation("a", "MAKES_TEA", "b")
    assert SemanticRelation("a", "TARGET", "b").relation == "TARGET"


def test_ontology_contains_master_prompt_actions_and_types():
    for a in ["ANALYZE", "COMPARE", "FIND", "CREATE", "DELETE", "CHECK", "TRANSLATE", "GENERATE", "CALCULATE", "SEARCH", "RETRIEVE", "EXECUTE", "UPDATE"]:
        assert a in ACTIONS
    assert type_of("sales") == "DATA" and type_of("report") == "ENTITY" and type_of("analyze") == "ACTION"


def test_config_is_loadable_and_not_hardcoded():
    cfg = load_config()
    assert cfg["severity"]["negation"] == "CRITICAL" and cfg["weights"]["negation"] >= cfg["weights"]["goal"]


def test_graph_from_frame_and_back():
    f = SemanticFrame(intent="REQUEST_ANALYSIS", actions=["ANALYZE"], data=["SALES"], time="Q1-2026", goal="")
    g = SemanticGraph.from_frame(f)
    assert {n.type for n in g.nodes} >= {"ACTION", "DATA", "TIME", "INTENT"}
    assert any(e.relation == "TARGET" for e in g.edges) and any(e.relation == "TIME" for e in g.edges)
    c = g.canonical()
    assert c["actions"] == ("ANALYZE",) and c["data"] == ("SALES",) and c["time"] == ("Q1-2026",)
    back = g.to_frame()
    assert back.actions == ["ANALYZE"] and back.data == ["SALES"] and back.time == "Q1-2026"


def test_negation_becomes_modality_not_a_separate_action():
    f = SemanticFrame(intent="REQUEST_EXECUTION", actions=["DELETE"], entities=["REPORT"], negations=["NO_DELETE"], constraints=["FORBID_DELETE"])
    c = SemanticGraph.from_frame(f).canonical()
    assert c["negation"] == ("FORBID:DELETE",) and c["actions"] == ("DELETE",) and c["constraints"] == ()


def test_graph_json_roundtrip():
    f = SemanticFrame(intent="REQUEST_ANALYSIS", actions=["ANALYZE"], data=["SALES"], time="Q2-2026")
    g = SemanticGraph.from_frame(f)
    assert SemanticGraph.from_dict(g.to_dict()).canonical() == g.canonical()
