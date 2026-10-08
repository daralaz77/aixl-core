"""Self-hosted local-model translator route (aixl/translators/local_translator.py, aixl/translators/
auto.py's 'local' mode), built 2026-10-01 after real fine-tuning work measured F1 0.6928 against blind5
— documented honestly in distill/README.md as a below-rule-based offline fallback, not a production
accuracy route. No real Ollama server is used here — `httpx.post` is mocked so these tests are fast,
deterministic, and run in CI without a local model pulled.

Skipped automatically if `httpx` is not installed, same guard and same reason as test_llm_translator.py."""
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("httpx")

from aixl.translators import local_translator  # noqa: E402
from aixl.translators.auto import to_graph_auto
from aixl.translators.natural_to_semantic import to_graph as rule_based_to_graph


def _fake_response(text: str, status: int = 200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {"message": {"content": text}}
    resp.raise_for_status = MagicMock()
    return resp


def test_default_mode_is_rule_based_and_unchanged(monkeypatch):
    monkeypatch.delenv("AIXL_TRANSLATOR_MODE", raising=False)
    text = "Analiza las ventas de Q1 2026."
    assert to_graph_auto(text).canonical() == rule_based_to_graph(text).canonical()


def test_translate_via_local_parses_a_well_formed_response():
    aixl_line = "V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES T:Q1-2026"
    with patch("httpx.post", return_value=_fake_response(aixl_line)) as mock_post:
        g = local_translator.translate_via_local("Analiza las ventas de Q1 2026.")
    assert g is not None
    assert g.canonical()["actions"] == ("ANALYZE",)
    # confirms the short fixed system prompt was sent, not the full card
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["messages"][0]["content"] == local_translator.SYSTEM_PROMPT
    assert kwargs["json"]["messages"][1]["content"] == "Analiza las ventas de Q1 2026."
    assert kwargs["json"]["options"]["temperature"] == 0.0


def test_translate_via_local_tolerates_a_stray_code_fence():
    aixl_line = "```\nV:AIXL-0.3 I:REQUEST_EXECUTION A:DELETE D:REPORT\n```"
    with patch("httpx.post", return_value=_fake_response(aixl_line)):
        g = local_translator.translate_via_local("Elimina el reporte.")
    assert g is not None
    assert g.canonical()["actions"] == ("DELETE",)


def test_translate_via_local_falls_back_to_none_on_garbage_response():
    with patch("httpx.post", return_value=_fake_response("no soy AIXL, lo siento")):
        g = local_translator.translate_via_local("Analiza las ventas.")
    assert g is None


def test_translate_via_local_falls_back_to_none_on_connection_error():
    with patch("httpx.post", side_effect=OSError("connection refused")):
        g = local_translator.translate_via_local("Analiza las ventas.")
    assert g is None


def test_local_mode_uses_the_local_result_when_the_call_succeeds(monkeypatch):
    monkeypatch.setenv("AIXL_TRANSLATOR_MODE", "local")
    aixl_line = "V:AIXL-0.3 I:REQUEST_EXECUTION A:DELETE D:REPORT"
    with patch("httpx.post", return_value=_fake_response(aixl_line)):
        g = to_graph_auto("Elimina el reporte.")
    assert g.canonical()["actions"] == ("DELETE",)


def test_local_mode_falls_back_to_rule_based_when_ollama_is_unreachable(monkeypatch):
    monkeypatch.setenv("AIXL_TRANSLATOR_MODE", "local")
    with patch("httpx.post", side_effect=OSError("connection refused")):
        g = to_graph_auto("Elimina el reporte.")
    assert g.canonical() == rule_based_to_graph("Elimina el reporte.").canonical()
