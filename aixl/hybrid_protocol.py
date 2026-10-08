"""Two-step HYBRID protocol (arbiter proves, semantic vetoes) for callers that bring their OWN judges — the shape the MCP tools expose.

WHY two steps and not "the server calls an LLM": the core never calls a model (aixl/arbiter.py, aixl/semantic/hybrid.py), and MCP server-initiated
sampling is deprecated in the SDK this repo pins (SEP-2577). So the caller's agent is the judge:

  1. `prepare(a, b)`            -> the versioned arbiter rules (+ their id), the exact judge input line, the semantic track's cheap verdict.
  2. the caller runs TWO INDEPENDENT judges (separate contexts, ideally different models) on `judge_input` under `judge_system_prompt`
     and collects `SAME | DIFFERENT | UNSURE` from each.
  3. `decide(a, b, verdicts)`   -> `aixl.semantic.hybrid.decide`: SAME only if >= 2 valid judges ALL say SAME and the semantic track does not veto.

Measured (validation/hybrid_arbiter of the evolution engine, 160 pairs by other authors, Sonnet+Haiku judges, one pre-registered run): false-SAME 2.9 %
and SAME on 85.5 % of equivalents for the hybrid, vs 54.3 % false-SAME for the original rule-based comparator. Those numbers belong to the JUDGES + rules
(docs/EVIDENCE.md); this module only combines their verdicts, it cannot make a weak judge strong. Independence of the judges is the caller's responsibility."""
import json

from aixl import arbiter
from aixl.core.normalizer import sanitize_input
from aixl.semantic import compare_texts, hybrid_decide

ACTION = {"SAME": "treat as the same instruction",
          "DIFFERENT": "do NOT treat as the same instruction",
          "REVIEW": "conflict between the judges and the semantic veto: a person decides",
          "UNSURE": "sameness not proven: do not assume it"}
PROTOCOL = ["Run TWO independent judges (separate contexts; different models if possible) with `judge_system_prompt` as the system prompt and `judge_input` as the user message.",
            "Each judge answers one line: `pair<TAB>SAME|DIFFERENT|UNSURE<TAB>short reason`. Keep only the verdict word.",
            "Call aixl_hybrid_decide(a, b, judge_verdicts={'judge_1': ..., 'judge_2': ...}). One judge, or a missing/invalid verdict, can never produce SAME."]


def prepare(a: str, b: str) -> dict:
    sem = compare_texts(a, b)
    obf = sorted(set(sanitize_input(a)[1]) | set(sanitize_input(b)[1]))
    return {"rules_id": arbiter.rules_id(), "judge_system_prompt": arbiter.rules_text(),
            "judge_input": json.dumps({"id": "pair", "a": a, "b": b}, ensure_ascii=False),
            "expected_judge_output": "pair\t<SAME|DIFFERENT|UNSURE>\t<short reason>",
            "semantic": {"verdict": sem.verdict, "flags": list(sem.flags)}, "obfuscation": obf, "protocol": PROTOCOL}


def decide(a: str, b: str, verdicts: dict) -> dict:
    """verdicts: {judge_name: 'SAME'|'DIFFERENT'|'UNSURE'} (anything else counts as an INVALID answer). Never raises on bad judge input."""
    judges = {str(n): (lambda _a, _b, v=v: v) for n, v in (verdicts or {}).items()}
    d = hybrid_decide(a, b, judges, retries=0)
    out = d.to_dict(); out["rules_id"] = arbiter.rules_id(); out["action"] = ACTION[d.verdict]
    out["judges_received"] = len(judges)
    return out
