"""2026-10-26 improvement round: number words, clock times, and the ES/PT homograph `dos` (a false EQUIVALENT from the published compare_verified)."""
import pytest

import aixl
from aixl.core.numberwords import canonical_numbers


@pytest.mark.parametrize("a,b", [
    ("Envie o relatório dos clientes.", "Envie o relatório aos dois clientes."),
    ("Exporte os dados dos clientes.", "Exporte os dados dos dois clientes."),
    ("Revise os pedidos dos clientes.", "Revise os pedidos de todos os clientes."),
])
def test_dos_never_yields_a_verified_equivalence(a, b):
    """`dos` is `2` in Spanish and `de + os` in Portuguese; it was read as 2 in both and `compare_verified` answered EQUIVALENT (verified)."""
    v = aixl.compare_verified(a, b)
    assert v["equivalent"] is False and v["verified"] is False
    from aixl.envelope import seal, verify
    assert verify(seal(a), b) != "MATCH"


def test_dos_is_reported_as_unaccounted():
    assert "dos" in aixl.compare_verified("Envie o relatório dos clientes.", "Envie o relatório aos dois clientes.")["unaccounted"]["a"]


@pytest.mark.parametrize("a,b", [
    ("Pay within fourteen days.", "Pay within fifteen days."),
    ("Paga en catorce días.", "Paga en quince días."),
    ("Pague em quatorze dias.", "Pague em quinze dias."),
    ("Pague em vinte e cinco dias.", "Pague em trinta e cinco dias."),
])
def test_number_words_beyond_ten_are_compared_by_the_core_and_by_relay_check(a, b):
    assert aixl.compare(a, b).equivalent is False
    assert aixl.relay_check(a, b)["ok"] is False


@pytest.mark.parametrize("text,expect", [
    ("within fourteen days", {"14"}), ("twenty-five days", {"25"}), ("treinta y cinco días", {"35"}), ("vinte e cinco dias", {"25"}),
    ("one hundred and five items", {"105"}), ("dois mil clientes", {"2000"}), ("dos mil", {"2000"}), ("ciento veinte", {"120"}),
    ("pay 1.250.000 pesos", {"1250000"}), ("pay 1,250,000 dollars", {"1250000"}), ("3,5 horas", {"3.5"}), ("the one that", set()),
])
def test_canonical_numbers(text, expect):
    assert canonical_numbers(text) == expect


@pytest.mark.parametrize("a,b", [
    ("Call me after 6 pm.", "Call me after 18:00."), ("Reunión a las 3:30 pm.", "Reunión a las 15:30."), ("Reunião às 15h30.", "Reunião às 3:30 pm."),
    ("Agenda a las 6 de la tarde.", "Agenda a las 18:00."), ("Within fourteen days.", "Within 14 days."),
])
def test_same_number_or_time_in_another_notation_is_not_a_change(a, b):
    assert aixl.relay_check(a, b)["ok"] is True


def test_a_different_clock_time_is_still_a_change():
    assert aixl.relay_check("Call me after 6 pm.", "Call me after 8 pm.")["ok"] is False


def test_relay_check_flags_a_changed_dos_count():
    assert aixl.relay_check("Envie o relatório dos clientes.", "Envie o relatório aos dois clientes.")["ok"] is False
    assert aixl.relay_check("Envie o relatório dos clientes.", "Envie o relatório dos clientes.")["ok"] is True


def test_portuguese_article_o_is_not_a_disjunction_even_after_a_politeness_prefix():
    src = "O gerente deve aprovar qualquer desconto acima de quinze por cento."
    assert aixl.relay_check(src, "Por favor, o gerente deve aprovar qualquer desconto acima de quinze por cento.")["ok"] is True
    assert aixl.relay_check("Envía el informe a Ana y a Luis.", "Envía el informe a Ana o a Luis.")["ok"] is False
