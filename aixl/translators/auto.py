"""Chooses between three translators, controlled by AIXL_TRANSLATOR_MODE. Default is 'rule_based' —
UNCHANGED behavior from before this module existed, so every existing test, benchmark, and deployment
keeps working exactly as before unless the user explicitly opts in.

Modes:
- 'rule_based' (default): always the rule-based translator (natural_to_semantic.py), exactly as before
  this module existed. Zero dependencies, ~88% accuracy, the safe default for anything not explicitly
  configured.
- 'llm' / 'auto': the live cloud LLM route (llm_translator.py, needs ANTHROPIC_API_KEY) — 93.5-96.5%
  measured accuracy, cross-vendor. **This is the recommended setting for production deployments** as of
  2026-10-01: it is the only route with real evidence of reaching the 90-95% target. Falls back to
  rule-based (with a warning logged) if the API call fails for any reason — never hard-fails a request.
- 'local': the self-hosted, fine-tuned-locally route (local_translator.py, needs Ollama running with the
  `aixl-distilled` model) — measured F1 0.6928, well below both other routes. Use only when a deployment
  must run fully offline with no API key and no internet, per distill/README.md's honest evidence trail.
  Falls back to rule-based on any failure, same contract as 'llm'.

This is what aixl/api/service.py's public functions (to_semantic, compare, translate, ...) call instead
of the rule-based to_graph() directly — so the deployed MCP/A2A agent benefits automatically. Benchmarks
that import aixl.translators.natural_to_semantic.to_graph directly are completely unaffected: they
measure the pure rule-based route on purpose and must keep doing so."""
import logging
import os
from datetime import date

from aixl.translators.natural_to_semantic import to_graph as _rule_based_to_graph

log = logging.getLogger("aixl.translators.auto")


def to_graph_auto(text: str, today: date | None = None):
    mode = os.environ.get("AIXL_TRANSLATOR_MODE", "rule_based")
    if mode in ("llm", "auto"):
        from aixl.translators.llm_translator import translate_via_llm
        g = translate_via_llm(text, today)
        if g is not None:
            return g
        log.warning("AIXL_TRANSLATOR_MODE=%s but the LLM route returned nothing usable; "
                    "falling back to the rule-based translator for this request", mode)
    elif mode == "local":
        from aixl.translators.local_translator import translate_via_local
        g = translate_via_local(text, today)
        if g is not None:
            return g
        log.warning("AIXL_TRANSLATOR_MODE=local but the local route returned nothing usable; "
                    "falling back to the rule-based translator for this request")
    return _rule_based_to_graph(text, today)
