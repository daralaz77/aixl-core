"""Live LLM-translator route (aixl/translators/llm_translator.py, aixl/translators/auto.py), built
2026-10-01 at the user's explicit request after being shown the real evidence that the rule-based
translator plateaus at ~88% while the LLM route already measures 93.5-96.5% cross-vendor. No real
network call or API key is used here — `httpx.post` is mocked so these tests are fast, deterministic,
and run in CI without a secret. Real end-to-end verification against the actual Anthropic API happens
separately, with a real key, not committed to this repo (see DEPLOYMENT.md).

Skipped automatically if `httpx` (an optional dependency, see pyproject.toml's `llm` extra) is not
installed — found the hard way: without this guard, a clean venv with only `mcp` installed (which does
NOT pull in httpx, unlike `a2a-sdk[http-server]`) failed 7 of these tests with ModuleNotFoundError at
collection time, not a clean skip."""
from unittest.mock import patch, MagicMock

import pytest

pytest.importorskip("httpx")

from aixl.translators import llm_translator  # noqa: E402
from aixl.translators.auto import to_graph_auto
from aixl.translators.natural_to_semantic import to_graph as rule_based_to_graph


def test_default_mode_is_rule_based_and_unchanged(monkeypatch):
    monkeypatch.delenv("AIXL_TRANSLATOR_MODE", raising=False)
    text = "Analiza las ventas de Q1 2026."
    assert to_graph_auto(text).canonical() == rule_based_to_graph(text).canonical()


def test_llm_mode_falls_back_to_rule_based_with_no_api_key(monkeypatch):
    monkeypatch.setenv("AIXL_TRANSLATOR_MODE", "llm")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text = "Elimina el reporte."
    assert to_graph_auto(text).canonical() == rule_based_to_graph(text).canonical()


def test_translate_via_llm_returns_none_without_an_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm_translator.translate_via_llm("Analiza las ventas.") is None


def _fake_response(text: str, status: int = 200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {"content": [{"type": "text", "text": text}]}
    resp.raise_for_status = MagicMock()
    return resp


def test_translate_via_llm_parses_a_well_formed_real_shaped_response():
    aixl_line = "V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES T:Q1-2026"
    with patch("httpx.post", return_value=_fake_response(aixl_line)) as mock_post:
        g = llm_translator.translate_via_llm("Analiza las ventas de Q1 2026.", api_key="sk-test-fake")
    assert g is not None
    assert g.canonical()["actions"] == ("ANALYZE",)
    # confirms the card was actually sent as the (cached) system prompt, not an empty/placeholder one
    _, kwargs = mock_post.call_args
    system_text = kwargs["json"]["system"][0]["text"]
    assert "AIXL" in system_text
    assert kwargs["json"]["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kwargs["json"]["messages"][0]["content"] == "Analiza las ventas de Q1 2026."


def test_translate_via_llm_tolerates_a_stray_code_fence_around_the_line():
    aixl_line = "```\nV:AIXL-0.3 I:REQUEST_EXECUTION A:DELETE D:REPORT\n```"
    with patch("httpx.post", return_value=_fake_response(aixl_line)):
        g = llm_translator.translate_via_llm("Elimina el reporte.", api_key="sk-test-fake")
    assert g is not None
    assert g.canonical()["actions"] == ("DELETE",)


def test_translate_via_llm_falls_back_to_none_on_garbage_response():
    with patch("httpx.post", return_value=_fake_response("I'm sorry, I don't understand the request.")):
        g = llm_translator.translate_via_llm("Analiza las ventas.", api_key="sk-test-fake")
    assert g is None


def test_translate_via_llm_falls_back_to_none_on_unparseable_aixl():
    # looks like an AIXL line but is malformed (not valid per the codec's own grammar)
    with patch("httpx.post", return_value=_fake_response("V:AIXL-0.3 THIS IS NOT VALID AIXL AT ALL !!")):
        g = llm_translator.translate_via_llm("Analiza las ventas.", api_key="sk-test-fake")
    assert g is None


def test_translate_via_llm_falls_back_to_none_on_network_error():
    with patch("httpx.post", side_effect=OSError("connection refused")):
        g = llm_translator.translate_via_llm("Analiza las ventas.", api_key="sk-test-fake")
    assert g is None


def test_llm_mode_uses_the_llm_result_when_the_call_succeeds(monkeypatch):
    monkeypatch.setenv("AIXL_TRANSLATOR_MODE", "llm")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    aixl_line = "V:AIXL-0.3 I:REQUEST_EXECUTION A:DELETE D:REPORT"
    with patch("httpx.post", return_value=_fake_response(aixl_line)):
        g = to_graph_auto("Elimina el reporte.")
    assert g.canonical()["actions"] == ("DELETE",)


def test_llm_mode_falls_back_to_rule_based_when_the_call_fails(monkeypatch):
    monkeypatch.setenv("AIXL_TRANSLATOR_MODE", "llm")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    with patch("httpx.post", side_effect=OSError("timeout")):
        g = to_graph_auto("Elimina el reporte.")
    assert g.canonical() == rule_based_to_graph("Elimina el reporte.").canonical()
