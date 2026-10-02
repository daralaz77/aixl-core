"""Live LLM-translator route (built 2026-10-01, at the user's explicit request after being shown the
real evidence first: the rule-based translator plateaued at ~88% across 3 full improvement rounds —
E-XV, E-CODEC, E-DATE, each against a fresh blind set — while the SAME core (graph, comparator, drift)
fed by an LLM translator following `data/llm_translator/card_0.3.md` already measured 93.5-96.5 % across
FOUR independent vendors (Haiku, Sonnet, Gemini, ChatGPT). Pushing the rule-based route further has a
demonstrated ceiling; this is the one route with real, cross-vendor evidence of reaching 90-95 %.

Until now, every "LLM route" measurement in this project was a human/subagent manually running text
through a chat session and recording the output (see benchmarks/llm_translator_eval.py's own parsing of
pre-recorded answer files) — never a real, live, automated API call from inside the running service.
This module is that call, for real: one Anthropic Messages API request per text, system prompt = the
frozen card, asking for exactly one AIXL line back, decoded by the SAME unmodified `aixl_codec` every
other route uses — the core is untouched either way, only the translation step changes.

Additive and optional by design: on ANY failure (no API key, `httpx` not installed, network error,
timeout, a response that doesn't parse as valid AIXL) this returns None so the caller
(aixl/translators/auto.py) falls back to the rule-based translator. The deployed agent must keep
working with zero behavior change when no API key is configured — the default, and every existing
test's situation."""
import logging
import os
from datetime import date

log = logging.getLogger("aixl.llm_translator")

_CARD_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          "data", "llm_translator", "card_0.3.md")
_card_cache: str | None = None

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def _load_card() -> str:
    global _card_cache
    if _card_cache is None:
        with open(_CARD_PATH, encoding="utf-8") as fh:
            _card_cache = fh.read()
    return _card_cache


def _extract_aixl_line(text: str) -> str | None:
    """The model is told to answer with exactly one line; tolerate a stray code fence or extra
    whitespace a real model sometimes adds despite instructions, without guessing at anything it
    didn't actually say — the first line that looks like a real AIXL header wins, nothing invented."""
    for line in text.strip().splitlines():
        line = line.strip().strip("`").strip()
        if line.startswith("V:AIXL"):
            return line
    return None


def translate_via_llm(text: str, today: date | None = None, api_key: str | None = None,
                       model: str | None = None, timeout: float = 10.0):
    """Returns a decoded SemanticGraph, or None if the LLM route is unavailable or failed for any
    reason — never raises; see module docstring for why this must always be safe to fall back from.
    `today` is accepted for signature parity with the rule-based translator but unused: the frozen
    card has no notion of a reference clock (a known, documented gap — relative dates fall back to
    whatever the model infers, same as the original E-XV/E-DATE measurements)."""
    try:
        import httpx
    except ImportError:
        return None

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    model = model or os.environ.get("AIXL_LLM_MODEL", DEFAULT_MODEL)

    try:
        card = _load_card()
    except OSError:
        log.exception("could not load LLM translator card at %s", _CARD_PATH)
        return None

    system_prompt = (card + "\n\nRespond with EXACTLY one line: the AIXL encoding of the text below, "
                      "and nothing else — no explanation, no code fence, no leading/trailing text.")

    try:
        resp = httpx.post(
            API_URL,
            headers={"x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION,
                      "content-type": "application/json"},
            # cache_control on the (static, 19.5k-char) card: repeated calls within the 5-min ephemeral
            # window hit the cache instead of re-billing the full system prompt every time -- real cost
            # win for both production traffic and batch corpus generation (distill/generate_fresh_corpus.py).
            json={"model": model, "max_tokens": 300,
                  "system": [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                  "messages": [{"role": "user", "content": text}]},
            timeout=timeout,
        )
        resp.raise_for_status()
    except Exception:                                      # noqa: BLE001 — any network/API failure falls back
        log.warning("LLM translator API call failed, falling back to rule-based", exc_info=True)
        return None

    try:
        data = resp.json()
        raw = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    except Exception:                                      # noqa: BLE001
        log.warning("LLM translator response had an unexpected shape, falling back to rule-based", exc_info=True)
        return None

    aixl_line = _extract_aixl_line(raw)
    if aixl_line is None:
        log.warning("LLM translator response had no parseable AIXL line (%r), falling back to rule-based",
                     raw[:200])
        return None

    from aixl.serialization import aixl_codec
    try:
        return aixl_codec.decode(aixl_line)
    except aixl_codec.AixlError:
        log.warning("LLM translator produced AIXL that failed to decode (%r), falling back to rule-based",
                    aixl_line)
        return None
