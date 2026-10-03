"""GAP-1 / GAP-2 fixed 2026-10-02 (master prompt §71-73, demo §92)."""
import datetime
from aixl.api import service as S
from aixl.core.fingerprint import fingerprint_graph

T = datetime.date(2026, 10, 2)
DEMO = ["Busca el informe más reciente y envíalo a Ana.", "Search the latest report and send it to Ana",
        "Busque o relatório mais recente e envie-o para Ana"]


def rels(g): return {(e.source, e.relation, e.target) for e in g.edges}


def test_most_recent_is_a_constraint_and_not_lost():
    assert S.to_semantic(DEMO[0]).canonical()["constraints"] == ("ORDER=MOST_RECENT",)
    assert not S.compare(DEMO[0], "Busca el informe y envíalo a Ana.").equivalent
    assert S.detect_drift(DEMO[0], "Busca el informe y envíalo a Ana.").differences


def test_oldest_differs_from_most_recent():
    assert not S.compare("Busca el informe más reciente.", "Busca el informe más antiguo.").equivalent


def test_latest_n_is_still_select_not_order():
    c = S.to_semantic("Muestra los últimos 5 informes").canonical()
    assert not any(x.startswith("ORDER=") for x in c["constraints"])


def test_target_binds_to_send_and_result_dependency():
    for t in DEMO:
        g = S.to_semantic(t)
        search, send = sorted(g.by_type("ACTION"), key=lambda n: n.attributes["order"])
        assert (send.id, "TARGET", "reference_1") in rels(g)
        assert (send.id, "DEPENDS_ON", search.id) in rels(g)
        assert (send.id, "OBJECT", search.id) in rels(g)
        assert g.meta["composition"] == "SEQUENCE"


def test_no_dependency_without_anaphora():
    g = S.to_semantic("Busca el informe y envía el resumen a Ana.")
    assert not any(e.relation == "DEPENDS_ON" for e in g.edges)


def test_demo_converges_across_languages():
    assert len({fingerprint_graph(S.to_semantic(t), today=T) for t in DEMO}) == 1
