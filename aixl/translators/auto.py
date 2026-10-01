"""Chooses between the rule-based translator (aixl/translators/natural_to_semantic.py — always
available, deterministic, the one every benchmark measures as "rule-based") and the live LLM translator
(aixl/translators/llm_translator.py — optional, needs ANTHROPIC_API_KEY), controlled by
AIXL_TRANSLATOR_MODE. Default is 'rule_based' — UNCHANGED behavior from before this module existed, so
every existing test, benchmark, and deployment keeps working exactly as before unless the user
explicitly opts in by setting AIXL_TRANSLATOR_MODE and a real API key.

Modes:
- 'rule_based' (default): always the rule-based translator, exactly as before this module existed.
- 'llm': always attempt the LLM route; falls back to rule-based (with a warning logged) if it fails —
  never hard-fails the request just because the LLM route had a bad moment.
- 'auto': same fallback behavior as 'llm' today (both try LLM then fall back) — kept as a distinct name
  for a future where 'auto' might pick per-request based on something else (e.g. text length/cost);
  right now the two modes behave identically.

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
    return _rule_based_to_graph(text, today)
