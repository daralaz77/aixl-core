# Hybrid decision as an MCP mode (2026-10-08)

Tools: `aixl_hybrid_prepare(a, b)` and `aixl_hybrid_decide(a, b, judge_verdicts)`; logic in `aixl/hybrid_protocol.py`, thin wrappers in `aixl/mcp_server.py`.

## What it does
The semantic track (cheap, rule-based) is a loss detector and a **veto**; the only thing that can *prove* that two instructions mean the same is a strict 2-of-2 LLM arbiter (`aixl/arbiter.py`, rules `data/arbiter/rules_v1.txt`). `aixl_hybrid_decide` returns:

| result | when |
|---|---|
| `SAME` | at least two valid judges, **all** `SAME`, and the semantic track does not veto |
| `DIFFERENT` | any judge dissents |
| `REVIEW` | judges say `SAME` but the semantic track found a definitive difference or flags the text as ambiguous: a person decides |
| `UNSURE` | fewer than two valid judges, an invalid answer, or `UNSURE` from a judge: sameness is not proven |

## Why two steps (the server calls no model)
The core never calls a model, and MCP server-initiated sampling is deprecated in the pinned SDK (SEP-2577). So the **caller's agent is the judge**:

1. Call `aixl_hybrid_prepare(a, b)`: you get `judge_system_prompt` (the versioned arbiter rules), `rules_id`, `judge_input` (one JSON line) and the semantic verdict.
2. Run **two independent judges** (separate contexts, ideally different models) with that system prompt and input; each answers `pair<TAB>SAME|DIFFERENT|UNSURE<TAB>reason`.
3. Call `aixl_hybrid_decide(a, b, {"judge_1": "SAME", "judge_2": "SAME"})`.

## Evidence and limits (read before relying on it)
* Measured once, pre-registered, on 160 pairs written by other authors (`validation/hybrid_arbiter` in the evolution-engine project), judges Sonnet + Haiku under `rules_v1.txt`: false-SAME 2.9 % (3 of 105 non-equivalent pairs), SAME on 85.5 % of equivalents; the original rule-based comparator had 54.3 % false-SAME on the same pairs. Single run, judge answers can flip between runs (see `EVIDENCE.md`).
* Those numbers belong to the **judges and the rules**; this module only combines verdicts. A weak judge, or two judges that are really one context, voids them. Independence is the caller's responsibility.
* Two LLM calls per pair. Use it where a wrong `SAME` costs more than a review (destructive or financial instructions); treat `REVIEW` as a human queue.
* It does not certify equivalence of open text for legal or safety purposes, and it does not execute anything.
