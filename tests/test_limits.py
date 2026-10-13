"""Availability guard (consejo-5x audit): to_graph is O(n^2); the analysis refuses oversized input and the shipped layers degrade instead of hanging."""
import time

import pytest

from aixl.core.limits import DEFAULT_MAX_INPUT_CHARS, InputTooLarge, max_input_chars
from aixl.envelope import seal, verify
from aixl.gate import translate_gated
from aixl.translators.natural_to_semantic import to_graph

BIG = "Analiza las ventas de Q1 2026. " * 1000          # 31 KB, ~1.3 s before the limit existed


def test_default_limit_and_env_override(monkeypatch):
    assert max_input_chars() == DEFAULT_MAX_INPUT_CHARS == 16_384
    monkeypatch.setenv("AIXL_MAX_INPUT_CHARS", "100")
    assert max_input_chars() == 100
    monkeypatch.setenv("AIXL_MAX_INPUT_CHARS", "not-a-number")
    assert max_input_chars() == DEFAULT_MAX_INPUT_CHARS


def test_to_graph_refuses_over_the_limit_and_accepts_at_it():
    with pytest.raises(InputTooLarge):
        to_graph("a " * (DEFAULT_MAX_INPUT_CHARS // 2 + 1))
    to_graph("a " * (DEFAULT_MAX_INPUT_CHARS // 2))          # exactly at the limit: analysed


def test_gate_degrades_to_natural_fast_and_returns_the_text_untouched():
    t0 = time.perf_counter()
    g = translate_gated(BIG)
    assert time.perf_counter() - t0 < 1.0
    assert g["mode"] == "NATURAL" and g["reason"] == "input_too_large" and g["output"] == BIG and g["fingerprint"] is None


def test_envelope_makes_no_claim_about_oversized_text():
    e = seal(BIG)
    assert e["verifiable"] is False and e["fp"] is None
    assert verify(seal("Analiza las ventas."), BIG) == "UNVERIFIED"


@pytest.mark.parametrize("text", ["Analiza las ventas de Q1 2026. ", "Q1 2026 ", "1,2,3,", "de ", "no "])
def test_worst_known_patterns_just_under_the_limit_stay_fast(text):
    t = (text * (DEFAULT_MAX_INPUT_CHARS // len(text)))[:DEFAULT_MAX_INPUT_CHARS]
    t0 = time.perf_counter()
    translate_gated(t)
    assert time.perf_counter() - t0 < 3.0                    # was > 8 s at 80-120 KB; the cap bounds the cost, it does not fix the O(n^2)
