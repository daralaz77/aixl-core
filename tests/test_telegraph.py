"""Option A (docs/V1_PROMPT_AUDIT.md): telegraphic form round-trips by fingerprint; unknown words fail closed."""
import pytest

from aixl.core.fingerprint import fingerprint_graph as fp
from aixl.gate import compact
from aixl.serialization.aixl_codec import decode, encode
from aixl.telegraph import TelegraphError, from_telegraph, to_telegraph
from aixl.translators.natural_to_semantic import to_graph

CASES = ["Compara el dataset #77 con el dataset #81.", "Analiza las ventas de Q1 2026.", "Do not translate the report.",
         "Analiza los videos de esta semana.", "Envía el resultado a la empresa Acme.", "Analiza 1.000 registros.", "borra el modelo de Ollama"]


@pytest.mark.parametrize("t", CASES)
def test_roundtrip_fingerprint(t):
    g = to_graph(t)
    assert fp(decode(from_telegraph(to_telegraph(compact(encode(g)))))) == fp(g)


def test_unknown_word_fails_closed():
    with pytest.raises(TelegraphError):
        from_telegraph("analyze flurbo")
