"""Self-hosted translator route via a locally fine-tuned model served by Ollama (distill/, built
2026-10-01). Real, measured accuracy against blind5 (the held-out set, never seen in training):
F1 0.6928 after LoRA fine-tuning + consistency-corpus correction + temperature=0 decoding — well below
the rule-based translator (~88%) and far below the cloud LLM route (93.5-96.5%, llm_translator.py).

This route exists for ONE honest reason: it needs no internet connection and no API key, so it is the
only option when a deployment must work fully offline or without any third-party billing. It is NOT the
accuracy-competitive route and should never be the default production choice while the cloud route is
available — see distill/README.md for the full evidence trail of why distillation on a 1.5B model with
this project's reused training data plateaued here, and what it would take to push it further.

Unlike llm_translator.py's card_0.3.md system prompt (19.5k chars), the fine-tuned model was trained to
answer from a short fixed instruction — the rules live in its weights, not in the prompt, so inference
here stays fast and needs no large context.

Additive and optional by design: on ANY failure (Ollama not running, model not pulled, network error,
timeout, a response that doesn't parse as valid AIXL) this returns None so the caller
(aixl/translators/auto.py) falls back to the rule-based translator, same contract as llm_translator.py."""
import logging
import os
from datetime import date

log = logging.getLogger("aixl.local_translator")

DEFAULT_MODEL = "aixl-distilled"
DEFAULT_BASE_URL = "http://localhost:11434"

SYSTEM_PROMPT = (
    "You are an AIXL 0.3 encoder. Given an instruction in Spanish, English or Portuguese, output "
    "its AIXL encoding as exactly one line starting with V:AIXL-0.3. Output only that line, nothing else."
)


def _extract_aixl_line(text: str) -> str | None:
    for line in text.strip().splitlines():
        line = line.strip().strip("`").strip()
        if line.startswith("V:AIXL"):
            return line
    return None


def translate_via_local(text: str, today: date | None = None, model: str | None = None,
                         base_url: str | None = None, timeout: float = 30.0):
    """Returns a decoded SemanticGraph, or None if the local route is unavailable or failed for any
    reason — never raises; see module docstring for why this must always be safe to fall back from.
    `today` is accepted for signature parity with the other translators but unused (same gap as
    llm_translator.py: the fine-tuned model has no reference-clock notion)."""
    try:
        import httpx
    except ImportError:
        return None

    model = model or os.environ.get("AIXL_LOCAL_MODEL", DEFAULT_MODEL)
    base_url = base_url or os.environ.get("AIXL_LOCAL_BASE_URL", DEFAULT_BASE_URL)

    try:
        resp = httpx.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "stream": False,
                "options": {"temperature": 0.0},
            },
            timeout=timeout,
        )
        resp.raise_for_status()
    except Exception:                                      # noqa: BLE001 — any network/Ollama failure falls back
        log.warning("Local translator call failed (Ollama not running / model not pulled?), "
                    "falling back to rule-based", exc_info=True)
        return None

    try:
        raw = resp.json().get("message", {}).get("content", "")
    except Exception:                                      # noqa: BLE001
        log.warning("Local translator response had an unexpected shape, falling back to rule-based",
                    exc_info=True)
        return None

    aixl_line = _extract_aixl_line(raw)
    if aixl_line is None:
        log.warning("Local translator response had no parseable AIXL line (%r), falling back to rule-based",
                     raw[:200])
        return None

    from aixl.serialization import aixl_codec
    try:
        return aixl_codec.decode(aixl_line).mark_model_derived("local")
    except aixl_codec.AixlError:
        log.warning("Local translator produced AIXL that failed to decode (%r), falling back to rule-based",
                    aixl_line)
        return None
