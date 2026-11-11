# Hybrid decision as an MCP mode (2026-10-08)

Tools: `aixl_hybrid_prepare(a, b)` and `aixl_hybrid_decide(a, b, judge_verdicts, strict=False)`; logic in `aixl/hybrid_protocol.py`, thin wrappers in `aixl/mcp_server.py`.

## What it does
The semantic track (cheap, rule-based) is a loss detector and a **veto**; the only thing that can *prove* that two instructions mean the same is a strict 2-of-2 LLM arbiter (`aixl/arbiter.py`, rules `data/arbiter/rules_v1.txt`). `aixl_hybrid_decide` returns:

| result | when |
|---|---|
| `SAME` | at least two valid judges, **all** `SAME`, and the semantic track does not veto |
| `DIFFERENT` | any judge dissents |
| `REVIEW` | judges say `SAME` but the semantic track found a definitive difference or flags the text as ambiguous: a person decides |
| `UNSURE` | fewer than two valid judges, an invalid answer, or `UNSURE` from a judge: sameness is not proven |

## Strict mode (`strict: true`, 2026-11-06): use it before an irreversible action
With `strict: true`, `SAME` also requires the rule-based comparator (`compare_texts`) to **prove** `EQUIVALENT`. When it cannot (it says `INCONCLUSIVE`), a unanimous `SAME` becomes `REVIEW` and a person decides. Dissent (`DIFFERENT`), the semantic veto and the "fewer than two valid judges" rules are unchanged: strict only ever makes the result more cautious.

Measured on the 640 pairs of blind19-26 (Opus and Sonnet judges under `arbiter_rules_v1`, one pass, other authors' text; the comparator was tuned on blind19-25, so only blind26 is out of sample for it):

| rule | false SAME on non-equivalent pairs | equivalent pairs accepted |
|---|---|---|
| two judges, no veto | 24 of 342 (7.0%) on blind19-25; 3 of 53 (5.7%) on blind26 | 196 of 218; 25 of 27 |
| default hybrid (judges + veto) | 19 of 342 (5.6%); 3 of 53 (5.7%) | 175 of 218; 19 of 27 |
| strict hybrid (comparator must prove EQUIVALENT) | 0 of 342; 0 of 53 | 11 of 218; **0 of 27** |

Read it plainly: strict accepts almost nothing, so almost every pair goes to review; that is the price. The 0 of 53 on blind26 is vacuous (the comparator accepted none of the 80 pairs, so it could not accept a wrong one), and the 0 of 342 comes from code corrected after looking at those pairs. It is **not** a claim that strict mode never fails; it is evidence that requiring a rule-based proof on top of the judges removed every false SAME we measured, because the comparator's errors and the judges' errors overlapped in 2 of 342 pairs on the frozen code. The two judges erred together far more than chance (24 both-SAME against about 3 expected), so adding a third LLM judge is not a substitute. Labels are the authors' (models), judges and authors are the same model family, and the 3 blind26 false SAMEs are all labelled UNDECIDABLE and are arguable.

A second, out-of-family check used **human-labelled** pairs from two public corpora (`data/blind27`, 100 pairs: PAWS-X Spanish and CondaQA negation edits; pre-registered, one run). There the comparator accepted none of the 100 pairs, so strict mode is again vacuous (0 of 50 equivalent pairs proven: on natural sentences outside its closed vocabulary, strict sends everything to review). The two judges together gave 1 false SAME of 50 non-equivalent pairs (2.0%, the one arguable PAWS label) and accepted 28 of 50 equivalent ones; the default hybrid gave 1 of 50 and accepted 24. All 20 CondaQA negation edits were rejected. So the 5-6% above came from subtle, model-written, partly UNDECIDABLE-labelled pairs, and the judges did better on human labels; both are small samples, the domain is encyclopedic statements rather than agent instructions, and neither is a generalisation claim.

A third check wrote pairs **inside the comparator's own constructs** (bounds, exceptions, exclusivity, negation, number forms, deadlines, verb synonyms, word order, quantifiers), so the strict rule can finally accept something. On `data/blind28` (120 pairs, pre-registered, one run) the comparator proved 24 of 60 equivalent pairs and accepted 4 of 60 non-equivalent ones (3 UNDECIDABLE-labelled and arguable); both Claude judges accepted every one of those 4 as well, so requiring them removed nothing, and the two judges again erred together (6 of 6 in common, 1.1 expected). A local non-Claude judge (Qwen2.5-7B Q4) said SAME to 94 of 120 pairs and accepted 35 of 60 non-equivalent ones: not a useful third judge. On `data/blind29` (120 fresh pairs, old versus new comparator on the same pairs) strict mode (comparator AND both judges) accepted 1 of 60 non-equivalent pairs and 31 of 60 equivalent ones, against 7 of 60 and 60 of 60 for the judges alone. That is the shape of the trade-off: about half the recall for roughly a seventh of the false accepts. Neither is a generalisation claim: the constructs are the ones the comparator was tuned on, authors and judges are Claude models, and one passing set after earlier failing ones is weak evidence.

On `data/blind30` (120 fresh pairs, paired against v0.7.0, with the two targeted constructs over-sampled) neither version of the comparator accepted a single one of the 60 non-equivalent pairs and both proved about half of the equivalent ones (28 and 30 of 60), so comparator AND both judges had 0 false accepts and 30 of 60 proven equivalents, against 6 of 60 and 60 of 60 for the judges alone. The change under test added only +2 proven pairs in the targeted constructs; the pre-registered +5 was not reached.

## Why two steps (the server calls no model)
The core never calls a model, and MCP server-initiated sampling is deprecated in the pinned SDK (SEP-2577). So the **caller's agent is the judge**:

1. Call `aixl_hybrid_prepare(a, b)`: you get `judge_system_prompt` (the versioned arbiter rules), `rules_id`, `judge_input` (one JSON line) and the semantic verdict.
2. Run **two independent judges** (separate contexts, ideally different models) with that system prompt and input; each answers `pair<TAB>SAME|DIFFERENT|UNSURE<TAB>reason`.
3. Call `aixl_hybrid_decide(a, b, {"judge_1": "SAME", "judge_2": "SAME"})`.

## Evidence and limits (read before relying on it)
* Measured once, pre-registered, on 160 pairs written by other authors (`validation/hybrid_arbiter` in the evolution-engine project), judges Sonnet + Haiku under `rules_v1.txt`: false-SAME 2.9 % (3 of 105 non-equivalent pairs), SAME on 85.5 % of equivalents; the original rule-based comparator had 54.3 % false-SAME on the same pairs. Single run, judge answers can flip between runs (see `EVIDENCE.md`).
* A later, harder measurement (blind19-26, see "Strict mode") found false SAME of about 5-6% for the default hybrid, not 2.9%: the families there were chosen to be subtle. Treat 2.9% as the easy case.
* Those numbers belong to the **judges and the rules**; this module only combines verdicts. A weak judge, or two judges that are really one context, voids them. Independence is the caller's responsibility.
* Two LLM calls per pair. Use it where a wrong `SAME` costs more than a review (destructive or financial instructions); treat `REVIEW` as a human queue.
* It does not certify equivalence of open text for legal or safety purposes, and it does not execute anything.
