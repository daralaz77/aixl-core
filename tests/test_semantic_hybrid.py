"""Hybrid decision: the arbiter proves sameness, the semantic track vetoes / hints. Judges are fakes: the core never calls a model."""
from aixl.semantic import hybrid_decide as H

SAME = lambda a, b: "SAME"
DIFF = lambda a, b: "DIFFERENT"
UNS = lambda a, b: "UNSURE"
BOTH_SAME = {"j1": SAME, "j2": SAME}


def test_sameness_requires_the_arbiter():
    assert H("Cierra la caja.", "Cierra la caja.").verdict == "UNSURE"                      # semantic alone never proves SAME
    r = H("Envía el informe antes del viernes.", "Remite el reporte antes del viernes.", BOTH_SAME)
    assert r.verdict == "SAME" and r.proven_by in ("arbiter", "arbiter+semantic")


def test_any_judge_dissent_blocks_sameness():
    r = H("Envía el informe.", "Envía el informe.", {"j1": SAME, "j2": DIFF})
    assert r.verdict == "DIFFERENT" and r.proven_by == "arbiter-dissent"


def test_semantic_veto_turns_a_false_same_into_review():
    r = H("Envía el informe antes del viernes.", "Envía el informe después del viernes.", BOTH_SAME)     # two judges wrongly say SAME
    assert r.verdict == "REVIEW" and r.semantic.verdict == "NOT_EQUIVALENT" and "time" in r.notes[0]


def test_semantic_alone_flags_a_suspected_difference_but_never_same():
    r = H("Envía el informe antes del viernes.", "Envía el informe después del viernes.")
    assert r.verdict == "DIFFERENT" and r.proven_by == "semantic-suspect"


def test_short_circuit_skips_the_judges():
    called = []
    def j(a, b): called.append(1); return "SAME"
    r = H("Envía el informe antes del viernes.", "Envía el informe después del viernes.", {"j1": j, "j2": j}, short_circuit=True)
    assert r.verdict == "DIFFERENT" and not called


def test_unsure_arbiter_with_semantic_suspicion_is_a_hint_not_a_verdict():
    r = H("Envía el informe antes del viernes.", "Envía el informe después del viernes.", {"j1": UNS, "j2": UNS})
    assert r.verdict == "UNSURE" and r.notes


def test_he_vs_she_cannot_become_same():                      # the blind16 false-equivalent class: even two wrong judges do not get a SAME through
    r = H("Dale a él el informe.", "Dale a ella el informe.", BOTH_SAME)
    assert r.verdict == "REVIEW"


def test_decisions_are_memoised(tmp_path):
    from aixl.arbiter import DecisionMemo
    calls = []
    def j(a, b): calls.append(1); return "SAME"
    memo = DecisionMemo(str(tmp_path / "m.jsonl"))
    H("Cierra la caja.", "Cierra la caja ya.", {"j1": j, "j2": j}, memo)
    n = len(calls)
    H("Cierra la caja.", "Cierra la caja ya.", {"j1": j, "j2": j}, memo)
    assert len(calls) == n


# ---- ambiguity veto (2026-10-03, after blind17: X024 slipped through with both judges SAME and the semantic model only INCONCLUSIVE) -------------------
def test_ambiguity_flag_turns_a_judges_same_into_review():
    r = H("No es cierto que no debas cifrar las copias de seguridad.", "Debes cifrar las copias de seguridad.", BOTH_SAME)
    assert r.verdict == "REVIEW" and r.semantic.verdict == "INCONCLUSIVE" and "AMBIGUOUS_DOUBLE_NEGATION" in r.notes[0]


def test_ambiguity_veto_does_not_touch_unflagged_inconclusive_pairs():
    r = H("Revisa los extintores cada mes.", "Los extintores deben inspeccionarse mensualmente.", BOTH_SAME)       # lexical gap only: no ambiguity flag
    assert r.verdict == "SAME"


def test_ambiguity_veto_is_not_applied_to_identical_texts():
    assert H("No todos los pedidos requieren firma.", "No todos los pedidos requieren firma.", BOTH_SAME).verdict == "SAME"


def test_flags_are_exposed_on_the_semantic_verdict():
    from aixl.semantic import compare_texts
    assert "AMBIGUOUS_NEGATED_ALL" in compare_texts("No borres todos los archivos.", "No borres ningún archivo.").flags
