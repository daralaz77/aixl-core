"""Phase 3: the public completeness API (aixl.core.completeness.is_complete) is the single condition under which AIXL may replace natural text."""
import pytest

from aixl.core.completeness import AFFIRM, is_complete, strict_complete
from aixl.translators.natural_to_semantic import to_graph


@pytest.mark.parametrize("text", ["Compara el documento 1 con el documento 2.", "Analiza las ventas de Q1 2026.", "Do not translate the report."])
def test_structured_instructions_are_complete(text):
    assert is_complete(text, to_graph(text))


@pytest.mark.parametrize("text", ["creo que ya revisa", "redacta el correo", "si muestrame", "ya me logee por favor correlo tu", "Hola"])
def test_dropped_context_is_not_complete(text):
    assert not is_complete(text, to_graph(text))


def test_strict_is_stricter_than_base_never_looser():
    from aixl.core.completeness import check_completeness
    for t in ["creo que ya revisa", "Analiza las ventas.", "Hola"]:
        g = to_graph(t)
        assert is_complete(t, g) == (bool(check_completeness(t, g).get("complete")) and strict_complete(t, g))


def test_affirmation_list_is_public_and_closed():
    assert {"si", "yes", "ok"} <= AFFIRM
