---
name: aixl-core
description: AIXL experimental Semantic Core (ES/EN/PT) — canonical meaning graph, AIXL serialization, comparator/diff/drift/ambiguity/contradiction, fingerprint, MCP/A2A adapters, plus the benchmark harness that measured all of it on other authors' text. Use when the user asks whether two instructions mean the same, wants to detect meaning changes between agents/models, or to build/test/benchmark/document AIXL. IMPORTANT status: for OPEN-DOMAIN text the strict full-text LLM arbiter (2 judges, 2-of-2) is the measured baseline; AIXL's rule/LLM routes are safe only as loss detectors and exact only in a controlled vocabulary. Separate from the aixl (0.1 lab) and aixl-translator (0.2) skills.
---

# AIXL Semantic Core 0.5.0 (executable) — state 2026-10-03; scope fixed in docs/adr/ADR-018.md
Root `~/.claude/skills/aixl-core/` (Python ≥ 3.11, `.venv` with pytest + tiktoken for dev). 616 tests (581 + 35 atom-layer). CI (GitHub Actions) runs the suite on Python 3.11 and 3.12.
**Read `docs/EVIDENCE.md` before answering any question about accuracy, safety, cost or "does AIXL work".** It is the single source of truth; this file only summarizes it.

## Use
```bash
cd ~/.claude/skills/aixl-core
.venv/bin/python cli.py compare "TEXT A" "TEXT B"      # verdict, similarity, drift, differences (rules route)
.venv/bin/python cli.py negotiate "SENDER TEXT" "RECEIVER TEXT" [--rounds N]
.venv/bin/python cli.py mcp-serve                      # real MCP server over stdio (needs: .venv/bin/pip install .[mcp])
.venv/bin/python -m aixl.agents.a2a_server 8766        # real A2A agent over HTTP (needs: .venv/bin/pip install .[a2a])
.venv/bin/python cli.py lab "A" "B"                    # Semantic Lab view; `cli.py serve` = web app
.venv/bin/python -m pytest -q                          # 616 tests
```
Python: `import aixl; aixl.compare(a, b)` (returns `.verdict` EQUIVALENT / NOT_EQUIVALENT / INCONCLUSIVE and `.equivalent`), `to_aixl`, `from_aixl`, `translate`, `semantic_diff`, `detect_drift`, `detect_ambiguity`, `detect_contradiction`, `semantic_fingerprint`, `negotiate`, `validate`, `round_trip`. Opt-in safety: `config["inconclusive"] = True` (see docs/COMPARATOR.md). Audit layer around an arbiter (ADR-018): `from aixl import arbiter` → `decide(a, b, judges={name: fn(a,b)->'SAME'|'DIFFERENT'|'UNSURE'}, memo=DecisionMemo(path))`, `consensus`, `parse_judge_lines`, `rules_text/rules_id` — you supply the judges; the core calls no model.

## What to tell the user (measured on OTHER authors' text; sets blind10/11/12 are spent)
* **Same meaning on open text?** Use the full-text arbiter, 2-of-2 (two independent LLMs read both texts under the strict rules in `data/blind10/arb_rules.txt`; "same" only if both say SAME; store the verdict). Result: blind12 359/360 true paraphrases recovered and **0/480 false "same"** on one-detail near-misses; blind11 100 % / 0.6 % false; repeatability: verdict flips 1.2 % for the 2-of-2; ≈ $0.28 per 1 000 pairs (estimate). Errors are systematic, so store decisions instead of re-deriving.
* **AIXL's own routes on open text are NOT safe**: the rules route called 40.6 % of non-equivalent pairs "equivalent" (blind11), 47–59 % on blind10, because the closed vocabulary drops what it has no slot for. With `inconclusive` on (completeness + structural markers + `R:` residue) false "equivalent" is 0–2 % but it proves only 0–17 % of true paraphrases (best AIXL-side pipeline 32 %). It is a loss detector, not a prover.
* **What AIXL is good for (measured):** exact, offline, free (0.85 ms/pair) comparison inside a controlled vocabulary; deterministic input hygiene (`sanitize_input`: invisible / look-alike characters); an interchange format with real MCP/A2A servers (clients of three vendors called it); drift/negotiation tooling. As a candidate-pair prefilter its key is worse than plain lexical overlap (recall 15.8 % vs 60.3 %).
* **Never claim:** AIXL proves equivalence of free-text paraphrases; 99.4 % / 95 %+ is general accuracy (those sets share the translator's vocabulary or its author); AIXL beats MCP/A2A/JSON or a strict LLM judge; it is a standard or universal; compression (AIXL is ≈ +246 % tokens vs the sentence). Never quote dev-200, 5×100 or demos as performance.
* **Not shown:** that AIXL adds correctness over the arbiter baseline; cross-vendor judges; real agent-to-agent traffic; embedding-based blocking; ES/EN/PT only, ≤ 360 cases per set, author-assigned labels.
* Rules-route ambiguity detection on free text: 16.7 % recall, 11.7 % false flags. Contradiction/ambiguity numbers from earlier (90 %/75 % on n = 20) are history only.
* Engineering facts (MCP/A2A adapters confirmed with Claude Desktop, ChatGPT/Codex and Antigravity; negotiation protocol; deployment and its 6 fixed bugs; CI) are verified and kept in `DEPLOYMENT.md`, `BENCHMARK.md` and the archive `docs/HISTORY.md`.

## AIXL 0.4 atom layer (2026-10-04) — `aixl/atoms/`, docs/ATOMS.md, docs/ATOMS_EVIDENCE.md, ADR-019
Concept-id atoms + typed relations (enforced endpoint types) + canonical fingerprint + wire format + semantic firewall (`receive`: MALFORMED / UNSUPPORTED_CONCEPT / SEMANTIC_INTEGRITY_FAILURE) + common profile + alignment + `diff` + per-dimension fidelity; `unrepresented` makes loss explicit. CLI: `cli.py atoms-extract|atoms-wire|atoms-receive|atoms-diff`. Annotation guide: docs/ATOM_MODEL.md (later sections win). 610 tests.
**Natural text:** `aixl.atoms.llm_extract` (ADR-020) = prompt builder + validator + k≥2 calls + abstain; on blind3 policy `core` accepts 67 % at core F1 0.93 (0.67 when abstained), `exact` accepts 35 % at exact 0.63 (0.20 abstained). **Say:** verifiable interchange format and measuring instrument; across a 3-model hop F1 0.93 / core 0.97 (n = 40), equal to the floor between two independent readers. **Never say:** free text has a unique atom graph (Sonnet-vs-Opus exact-graph agreement on unseen text is ~35 %, F1 ≈ 0.83; three guide rounds 32.7→35.3→36.0 % = noise), that the rule extractor handles natural text (F1 0.27–0.37, declares 0/450 complete, 0 silent errors), or any dev number (93–98 % are tuning). The 2-of-2 arbiter (ADR-018) stays the baseline for free-text equivalence. Fable was unavailable (credits); a different annotator family on a new blind set is the open test.

## 0.3-R semantic track (2026-10-03) — separate from the 0.5.0 rules route
`aixl/semantic/` (`parse`, `compare_texts`, `hybrid_decide`; docs/SEMANTIC_MODEL_0_3R.md, evidence in docs/EVIDENCE.md §4b). A closed-domain loss/distortion detector with explicit ambiguity and a fail-closed three-state verdict, plus a hybrid where the 2-of-2 arbiter proves sameness and the semantic model vetoes (REVIEW). Measured on 6 independent sets: false-equivalent 0-6.8%, NOT_EQUIVALENT precision 55-87% (90% gate failed twice), proven equivalent ~0-2%, hybrid safer-than-arbiter claim NOT allowed. Never present NOT_EQUIVALENT as proven or the track as an equivalence prover. Tests: `tests/test_semantic_r.py`, `test_semantic_hybrid.py`, `test_golden_r_dataset.py`; data: `data/golden_r` (dev), `data/blind13-18` (spent).

## Where things are
`docs/EVIDENCE.md` (evidence + what to use for what) · `docs/adr/ADR-016.md`, `ADR-017.md` (designs, experiments, pre-registrations, results) · `LIMITATIONS.md` · `docs/HISTORY.md` (superseded status text, verbatim) · `data/blind10/` (frozen sets with sha256, all LLM outputs, so every table recomputes without new model calls) · `benchmarks/*_eval.py`.

## Working rules (from the master prompt)
Every bug → a test in `tests/test_regression.py`; every claim → a result file; new phrasing gaps go to a NEW blind set, not into the number you report. Docs: README, ARCHITECTURE, BENCHMARK, LIMITATIONS, PHASES; pre-registration in `BENCHMARK/PREREG_0.3.md`.
