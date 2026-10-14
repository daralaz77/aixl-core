"""layered_decide: deterministic proof first, the arbiter for the rest; a deterministic NOT_EQUIVALENT is a hint, never a verdict."""
from aixl.arbiter import layered_decide


def judges(*verdicts):
    return {f"j{i}": (lambda a, b, v=v: v) for i, v in enumerate(verdicts)}


def test_verified_equivalence_needs_no_judge():
    called = []
    j = {"x": lambda a, b: called.append(1) or "SAME", "y": lambda a, b: called.append(1) or "SAME"}
    r = layered_decide("Analiza las ventas de Q1 2026.", "Analyze Q1 2026 sales.", j)
    assert r.verdict == "SAME" and r.source == "deterministic" and not called


def test_deterministic_not_equivalent_is_not_final_the_arbiter_decides():
    # the core says NOT_EQUIVALENT (different words), two judges say SAME: the arbiter's answer stands (the hint is kept for the audit trail)
    a, b = "No se permite entrar a la obra sin casco.", "Para entrar a la obra es obligatorio llevar casco."
    r = layered_decide(a, b, judges("SAME", "SAME"))
    assert r.verdict == "SAME" and r.source == "arbiter" and r.deterministic in ("NOT_EQUIVALENT", "INCONCLUSIVE")


def test_one_dissenting_judge_makes_it_different_and_invalid_makes_it_unsure():
    a, b = "Borra el archivo temporal del servidor.", "Elimina el archivo temporal del servidor de pruebas."
    assert layered_decide(a, b, judges("SAME", "DIFFERENT")).verdict == "DIFFERENT"
    assert layered_decide(a, b, judges("SAME", "banana")).verdict == "UNSURE"
    assert layered_decide(a, b, judges("SAME")).verdict in ("UNSURE", "DIFFERENT")      # a single judge never proves SAME


def test_difference_reliable_flag_is_only_true_when_both_texts_are_accounted_for():
    import aixl
    d = aixl.compare_verified("Delete the old backups.", "Delete the new backups.")
    assert d["verdict"] == "NOT_EQUIVALENT" and d["difference_reliable"] is True
    d2 = aixl.compare_verified("No se permite entrar a la obra sin casco.", "Para entrar a la obra es obligatorio llevar casco.")
    if d2["verdict"] == "NOT_EQUIVALENT":
        assert d2["difference_reliable"] is False
