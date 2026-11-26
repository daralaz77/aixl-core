---
name: aixl-core
description: AIXL experimental Semantic Core (ES/EN/PT) — canonical meaning graph, AIXL serialization, comparator/diff/drift/ambiguity/contradiction, fingerprint, MCP/A2A adapters, plus the benchmark harness that measured all of it on other authors' text. Use when the user asks whether two instructions mean the same, wants to detect meaning changes between agents/models, or to build/test/benchmark/document AIXL. IMPORTANT status: for OPEN-DOMAIN text the strict full-text LLM arbiter (2 judges, 2-of-2) is the measured baseline; AIXL's rule/LLM routes are safe only as loss detectors and exact only in a controlled vocabulary. Separate from the aixl (0.1 lab) and aixl-translator (0.2) skills.
---

# AIXL Semantic Core 0.8.1 (executable) — state 2026-11-26; scope fixed in docs/adr/ADR-018.md
Root `~/.claude/skills/aixl-core/` (Python ≥ 3.11, `.venv` with pytest + tiktoken for dev). Wire token `V:AIXL-0.3`. 2151 tests collected; on 2026-11-26: 2150 pass, 1 expected failure (some need local ports or network, so they fail inside a sandbox). CI (GitHub Actions) runs the suite on Python 3.11 and 3.12. The GitHub repo `daralaz77/aixl-core` is **public** (MIT).
**Read `docs/EVIDENCE.md` before answering any question about accuracy, safety, cost or "does AIXL work".** It is the single source of truth; this file only summarizes it. Newest measurements: its §4e (blind19-34).

## Use
```bash
cd ~/.claude/skills/aixl-core
.venv/bin/python cli.py compare "TEXT A" "TEXT B"      # verdict, similarity, drift, differences (rules route)
.venv/bin/python cli.py negotiate "SENDER TEXT" "RECEIVER TEXT" [--rounds N]
.venv/bin/python cli.py mcp-serve                      # real MCP server over stdio (needs: .venv/bin/pip install .[mcp])
.venv/bin/python -m aixl.agents.a2a_server 8766        # real A2A agent over HTTP (needs: .venv/bin/pip install .[a2a])
.venv/bin/python cli.py lab "A" "B"                    # Semantic Lab view; `cli.py serve` = web app
.venv/bin/python -m pytest -q
```
Python: `import aixl; aixl.compare(a, b)` (returns `.verdict` EQUIVALENT / NOT_EQUIVALENT / INCONCLUSIVE and `.equivalent`), `to_aixl`, `from_aixl`, `translate`, `semantic_diff`, `detect_drift`, `detect_ambiguity`, `detect_contradiction`, `semantic_fingerprint`, `negotiate`, `validate`, `round_trip`. Opt-in safety: `config["inconclusive"] = True` (see docs/COMPARATOR.md). Audit layer around an arbiter (ADR-018): `from aixl import arbiter` → `decide(a, b, judges={name: fn(a,b)->'SAME'|'DIFFERENT'|'UNSURE'}, memo=DecisionMemo(path))`, `consensus`, `parse_judge_lines`, `rules_text/rules_id` — you supply the judges; the core calls no model.

**Hybrid over MCP** (docs/HYBRID_MCP.md): `aixl_hybrid_prepare(a, b)` returns the judge prompt, input and a `short_circuit` hint → run two independent judges → `aixl_hybrid_decide(a, b, verdicts, strict=False, veto="all")` → SAME / DIFFERENT / REVIEW / UNSURE. `strict=True` before an irreversible action; `veto="definite"` is opt-in for reversible ones.

## What to tell the user (measured on OTHER authors' text; spent sets)
* **Same meaning on open text?** Use the full-text arbiter, 2-of-2 (two independent LLMs read both texts under the strict rules in `aixl/resources/arbiter_rules_v1.txt`; "same" only if both say SAME; store the verdict). Best case: blind12 359/360 paraphrases recovered and 0/480 false "same" on one-detail near-misses; blind11 100 % / 0.6 % false. **On subtle later sets two judges had 2-12 % false "same"** (blind19-31), and 0/135 on blind33 (spent when judged). Quote the range, never 0/480 alone. ≈ $0.28 per 1 000 pairs (estimate, prices of 2026-09-25). Errors are systematic, so store decisions.
* **Before an irreversible action:** `strict=True` (judges AND comparator proof) gave 1/60, 0/60 and 0/63 false "same" in-vocabulary (blind29-31) while accepting about half of the equivalents; on blind28 it gave no protection (comparator's 4/60 false accepts passed both judges); outside the vocabulary it sends almost everything to review. Otherwise a person decides.
* **AIXL's own routes on open text are NOT safe**: the rules route (`aixl.compare`) called 40.6 % of non-equivalent pairs "equivalent" (blind11), 47–59 % on blind10. With `inconclusive` on, false "equivalent" is 0–2 % but it proves only 0–17 % of true paraphrases.
* **Rule comparator (`compare_texts`) is a loss detector, not a prover**: new families blind19-25 false accepts 16/342, `NOT_EQUIVALENT` precision 48/84, equivalents proven 14/218; inside its own constructs 40–52 % proven (blind28-31); blind33 0/135 false accepts but 1/135 proven. Never present `NOT_EQUIVALENT` as proven or promise "0 errors". blind34 (954 pairs, open-model authors) has very noisy labels: don't quote its raw counts as error rates.
* **Veto:** on 630 spent pairs the default veto caught no judge error and `veto="definite"` recovered equivalents (117 → 129 of 135); but on blind19-25 the default veto removed 5 false "same", and on blind34 the labels (noisy) show more false "same" with `definite` (125 vs 101 of 474). Not enough to change the default.
* **What AIXL is good for (measured):** exact, offline, free (0.85 ms/pair) comparison inside a controlled vocabulary; deterministic input hygiene (`sanitize_input`: invisible / look-alike characters); an interchange format with real MCP/A2A servers (clients of three vendors called it); drift/negotiation tooling. As a candidate-pair prefilter its key is worse than plain lexical overlap (recall 15.8 % vs 60.3 %).
* **Never claim:** AIXL proves equivalence of free-text paraphrases; 99.4 % / 95 %+ is general accuracy; AIXL beats MCP/A2A/JSON or a strict LLM judge; it is a standard or universal; compression (AIXL is ≈ +246 % tokens vs the sentence). Never quote dev-200, 5×100, audits used for tuning or demos as performance.
* **Not shown:** human-labelled evidence beyond 100 pairs; real agent-to-agent traffic; judges from other commercial vendors; embedding-based blocking; anything outside ES/EN/PT.
* Rules-route ambiguity detection on free text: 16.7 % recall, 11.7 % false flags.
* Engineering facts (MCP/A2A adapters confirmed with Claude Desktop, ChatGPT/Codex and Antigravity; negotiation protocol; deployment) are kept in `DEPLOYMENT.md`, `BENCHMARK.md` and `docs/HISTORY.md`.

## Current direction
Growing the comparator's closed lists has not met a pre-registered recall rule in blind29-33: prefer safety fixes. The next informative measurement needs human labels and real agent traffic. A rule change is merged only after a pre-registered paired run on a fresh set (unmerged examples: blind31, blind32); releases and changes are in `CHANGELOG.md` and `docs/SEMANTIC_CHANGELOG.md`.

## AIXL 0.4 atom layer (2026-10-04) — `aixl/atoms/`, docs/ATOMS.md, docs/ATOMS_EVIDENCE.md, ADR-019
Concept-id atoms + typed relations (enforced endpoint types) + canonical fingerprint + wire format + semantic firewall (`receive`: MALFORMED / UNSUPPORTED_CONCEPT / SEMANTIC_INTEGRITY_FAILURE) + common profile + alignment + `diff` + per-dimension fidelity; `unrepresented` makes loss explicit. CLI: `cli.py atoms-extract|atoms-wire|atoms-receive|atoms-diff`. Annotation guide: docs/ATOM_MODEL.md (later sections win).
**Natural text:** `aixl.atoms.llm_extract` (ADR-020) = prompt builder + validator + k≥2 calls + abstain. Replicated on a 2nd unseen set (pre-registered): accepted graphs score core F1 0.92 vs 0.70 abstained (pooled 300 texts); coverage 54–67 % (`core`) / 32–35 % (`exact`) — the pre-registered ≥55 % coverage floor failed by 1 point, claim downgraded to those ranges. **Say:** verifiable interchange format and measuring instrument; across a 3-model hop F1 0.93 / core 0.97 (n = 40), equal to the floor between two independent readers. **Never say:** free text has a unique atom graph (Sonnet-vs-Opus exact-graph agreement on unseen text ~35 %, F1 ≈ 0.83), that the rule extractor handles natural text (F1 0.27–0.37, declares 0/450 complete, 0 silent errors), or any dev number (93–98 % are tuning).

## 0.3-R semantic track — `aixl/semantic/`
`parse`, `compare_texts`, `hybrid_decide`; docs/SEMANTIC_MODEL_0_3R.md, evidence in docs/EVIDENCE.md §4b (blind13-18) and §4e (blind19-34). Closed-domain loss/distortion detector with explicit ambiguity and a fail-closed three-state verdict, plus the hybrid above. Tests: `tests/test_semantic_*.py`; data: `data/golden_r` (dev), `data/blind13-34` (spent).

## Internal guard — `aixl/guard`, docs/GUARD.md (status as of 2026-10-07, not re-checked)
Fail-closed PASS/REVIEW check for ReclamaYa petitions, CineMatch EN→ES error messages and Robot School instruction-vs-actions (`cli.py guard <profile> A B`). Measured: AIXL comparator ALONE lets 45-50 % of distortions through on open text; the rules layer makes it 0/183 on author-written sets (95 % bound ≈ 2 %; first-contact misses 0-4 per fresh set), and AIXL added no unique catches (advisory). Was deployed in code (uncommitted) in all three projects; Robot School shadow-mode only.

## Where things are
`docs/EVIDENCE.md` (evidence + what to use for what) · `docs/HYBRID_MCP.md` · `docs/adr/` (designs, experiments, pre-registrations) · `LIMITATIONS.md` · `docs/HISTORY.md` (superseded status text) · `data/blind*/` (frozen sets, PREREG, results; spent sets are never re-run for new claims) · `benchmarks/*_eval.py`.

## Working rules (from the master prompt)
Every bug → a test; every claim → a result file; new phrasing gaps go to a NEW blind set, not into the number you report. Docs: README, ARCHITECTURE, BENCHMARK, LIMITATIONS, PHASES; pre-registration in `BENCHMARK/PREREG_0.3.md`.
