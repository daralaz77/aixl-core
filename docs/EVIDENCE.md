# Evidence and recommended use (state 2026-10-03)

This page is the single source of truth for **what has been measured about AIXL and what it supports**. Every number links to a result file or to
[adr/ADR-017.md](adr/ADR-017.md) (full tables, setup, limits). If another document disagrees with this page, this page wins; superseded text is archived in
[HISTORY.md](HISTORY.md). Status labels follow master prompt §36: HYPOTHESIS · DESIGN · IMPLEMENTATION · EXPERIMENT · RESULT · LIMITATION.

## 1. What to use for what

| You need | Use | Why (RESULT) |
|---|---|---|
| Decide whether two **open-text** instructions (ES/EN/PT) mean the same | **Full-text arbiter, 2-of-2**: two independent LLMs read both original texts under strict rules (`data/blind10/arb_rules.txt`, texts treated as data); "same" only if both say SAME; **store the verdict** (decision memo) | 359–360/360 equivalent pairs recovered and **0/480 false "same" on the hardest near-miss negatives** (blind12); 100 % / 0.6 % false on blind11; 1 error in 70 attacks written to fool it |
| Exact, offline, free equivalence **inside a controlled vocabulary** | AIXL rules route (`aixl.compare`) | 99.4 % on the project's own 5×100 benchmark (same author as the code), 0.85 ms/pair. **No independent evidence of coverage**: on other authors' open text it is *not* safe (next row) |
| Detect that something was lost, never say "equal" without proof | AIXL with `inconclusive` on (opt-in; completeness + structural markers + `R:` residue) | False "equivalent" 47–59 % → 0–2 % on blind10/blind11, **but proves 0–17 % of true equivalents**: it is a loss detector, not a prover |
| Input hygiene against invisible characters / look-alike letters | `sanitize_input` (always applied by the translator) | 0 false rejections on 71 benign pairs; caught the Cyrillic-homoglyph class that a single cheap judge missed (post-hoc, one set) |
| Cheap candidate generation before an arbiter | A plain lexical overlap filter (**not** AIXL's key) | blind12: lexical Jaccard ≥ 0.1 keeps 60.3 % of equivalent pairs at 1.3 % of all pairs; AIXL canonical/fingerprint key keeps 15.8 % at 0.28 % |
| An interchange format with an audit trail | AIXL line + MCP/A2A adapters + stored decisions | Real clients from three vendors called the MCP server (engineering evidence, not accuracy); the format itself is not shown to improve meaning preservation |

**Do not** claim: that AIXL proves equivalence of free-text paraphrases; that the 99.4 % / 95 % figures are general accuracy; that AIXL is better than
sending both texts to a strict LLM judge (no measurement shows it adds correctness to that baseline); that it is a standard or universal.

## 2. The measurements, in order

All "blind" sets were written by a model **without access to the repository**; each is evaluated once and is then *spent* (no tuning on it afterwards).

| # | Set (authors) | What was run | Headline RESULT | Detail |
|---|---|---|---|---|
| 1 | Own 5×100 benchmark (same author as code) | rules route | 497/500 = 99.4 % | BENCHMARK.md. **Not independent**: inherits the translator's vocabulary |
| 2 | blind10 — 150 + 150 cases (Opus, Haiku) | rules route; LLM route (card 0.3) | **24.7–40.0 %** and **37.0 %**; ~60 % of non-equivalent pairs judged EQUIVALENT because the format has no slot for the rest of the meaning and drops it silently | LIMITATIONS.md E-BLIND10 |
| 3 | blind10 | AIXL-side repairs: `inconclusive`, `R:` residue, per-side completeness, typed keys | false "equivalent" → 0–2 %; proven equivalents only 2–17 % (typed keys 10 %, gate + residue judge 32 %) | ADR-016, ADR-017 |
| 4 | blind10 | full-text arbiter (Sonnet, Haiku, 2-of-2) | 56–60/60 proven, 0/180 false | ADR-017 |
| 5 | blind10 adversarial + red-team (Opus, told the arbiter's rules) | arbiter vs attacks (injection aimed at the judge, hidden negation, scope, locale, homoglyphs, role swap, conditionals, polarity, partial commit) | consensus fooled by 1/70; injection 0/8; single Haiku fooled by 4/70 | ADR-017 |
| 6 | blind10 subset, 82 pairs × 5 passes × 2 models | repeatability | verdict flips: Sonnet 1.2 %, Haiku 6.1 %, 2-of-2 1.2 %; errors are systematic, not noise | ADR-017 |
| 7 | **blind11** — 300 cases (Sonnet), run once | every arm (rules 0.4, rules+inconclusive, AIXL LLM route on two encoders, arbiter alone / 2-of-2 / + sanitizer / + AIXL gate) | rules 0.4: 50 % proven but **40.6 % false**; AIXL LLM route: 0 % proven; **arbiter 2-of-2: 100 % proven, 0.6 % false** | `data/blind10/blind11_result.txt` |
| 8 | **blind12** — 360 texts, 60 clusters, 2 new authors, run once | stage-1 candidate keys + stage-2 arbiter on 840 pairs | AIXL key recall 15.8 % (gate ≥ 80 % **failed**); lexical baseline 60.3 %; arbiter 2-of-2: 359/360 equivalent, **0/480** near-miss false "same" | `data/blind10/b12_stage1_result.txt`, `b12_stage2_result.txt` |

Pre-registered gates were written before blind11 and blind12 outputs existed (ADR-017 "PRE-REGISTRATION" sections). The arbiter passes them; the AIXL
semantic layers do not.

## 3. Cost and latency (estimates; no live API call was made)

Per 1 000 pairs, proxy tokenizer ±20 %, prices from the claude-api skill table cached 2026-09-25 (check before budgeting), thinking tokens not counted:

| Path | Latency | Cost |
|---|---|---|
| AIXL deterministic compare | 0.85 ms/pair (0.85 s per 1 000) | $0, offline |
| Arbiter Sonnet 5.5 | ≈ 3.5 min sequential (one call if parallel) | ≈ $0.16 |
| Arbiter Haiku 4.5 | ≈ 14.7 min sequential | ≈ $0.12 |
| **Arbiter 2-of-2** | max of the two in parallel | **≈ $0.28** (≈ $0.14 with Batch API) |
| AIXL LLM-route encoders (card 0.6) | 47–176 s per 90 texts | ≈ $1.13 Sonnet (≈ 7× the arbiter) and 0 % proven on blind11 |

The arbiter is paid **per pair** (all pairs over N texts = N(N−1)/2: N = 10 000 → ≈ $8–14 k); encoding is paid **per text** (N = 10 000 ≈ $6). A cheap
lexical stage 1 reduces arbiter calls ~77× at 60 % recall (blind12). Decision memos make each pair a one-time cost.

## 4. What is NOT shown (LIMITATION)

* Whether AIXL adds *correctness* over the arbiter baseline in any setting; its remaining candidate value is deterministic/offline exact proofs in controlled vocabularies, cacheable fingerprints for exact duplicates, a machine-checkable format and audit trail — none measured against the baseline except cost.
* Recall of any cheaper stage-1 design built after seeing blind12 (embedding-based blocking was not tested); false "same" on the 63 780 cross-cluster pairs in blind12 that were not judged.
* Only ES/EN/PT; only instruction-like texts; at most 360 cases per set; labels come from the authors (disputed ones are listed in ADR-017); judges are two model families from one vendor (cross-vendor judges not tested); arbiter prompts were fixed in advance but other wordings may shift recall/precision; no repeatability beyond 5 passes; arbiter latency measured through agents (includes harness overhead).
* AMBIGUOUS class: the rules route detects 16.7 % of ambiguous free-text instructions and flags 11.7 % of non-ambiguous ones (blind11); no arbiter arm was run for it.
* Nothing here is validated with real agent-to-agent traffic or any real organisation.
* The sanitizer-veto result (Haiku alone 4 → 1 false "same" on blind10-adversarial) was chosen after seeing the data and was neither confirmed nor refuted by blind11/12 (no obfuscation attacks in them).

## 5. Reproduce

```bash
cd ~/.claude/skills/aixl-core
.venv/bin/python -m pytest -q                                               # unit/regression/doc tests
.venv/bin/python -m benchmarks.sil5x100_eval                                # own benchmark (not independent)
.venv/bin/python -m benchmarks.blind10_eval data/blind10/haiku.jsonl        # rules route on another author's set
.venv/bin/python -m benchmarks.blind11_eval data/blind10                    # blind11, every arm (set is spent)
.venv/bin/python -m benchmarks.funnel_eval stage1                           # blind12 stage 1 (deterministic)
.venv/bin/python -m benchmarks.funnel_eval stage2 data/blind10              # blind12 stage 2
.venv/bin/python -m benchmarks.repeatability_eval data/blind10              # arbiter repeatability
```
Frozen sets carry their sha256 (`data/blind10/blind11.sha256`, `blind12.sha256`); verify with `shasum -a 256 -c`. LLM outputs are stored next to each set so every table can be recomputed without new model calls.
