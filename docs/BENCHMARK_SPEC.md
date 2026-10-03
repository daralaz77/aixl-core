# Benchmark specification

Principle: *was the operational meaning preserved?*, not *does the text look right?* Every number below says who authored the data and whether it was seen before tuning.

## Instruments
| Instrument | n | Authors / independence | Command | Use |
|---|---|---|---|---|
| dev-200 | 200 | the code's author | `python cli.py bench` | demo / smoke only |
| blind sets 1–9 | ≈200 each (100 EQ + 100 NEQ, ≥30 minimal pairs among the NEQ) | fresh model authors (Sonnet; set 5 by Gemini and ChatGPT) | `python -m benchmarks.blind_eval --round N` (1–4 rule-based) | **the only generalisation evidence**; first run = evidence, then contaminated |
| 5×100 (§42) | 500 | generated, same author as the code, seed 20261002 | `python -m benchmarks.sil5x100_eval` | coverage + regression ratchet |
| security §39 | 450 combinatorial + 57 hard + 31 controls | generated + hand-written, same author | `python -m benchmarks.sil_security_eval` | adversarial regression ratchet |
| interop / negotiation / xv | see BENCHMARK.md §7–§16 | cross-vendor LLM encoders | `benchmarks/interop_eval.py` etc. | cross-model consistency |
| **blind10** (spent) | 150 + 150 cases, 5 classes; + 198 adversarial/red-team pairs | Opus, Haiku, Sonnet (no repository access); red-team by Opus | `benchmarks/blind10_eval.py`, `blind10_llm_eval.py`, `arbiter_eval.py`, `adversarial_eval.py`, `repeatability_eval.py` | first benchmark by other authors; diagnosis set (so no longer a clean judge) |
| **blind11** (spent, run once) | 300 cases (60 per class) | Sonnet; sha256 frozen | `benchmarks/blind11_eval.py` | pre-registered one-shot judge: every arm |
| **blind12** (spent, run once) | 360 texts = 60 clusters × 4 paraphrases + 120 near-misses (64 620 pairs) | Opus and Sonnet; sha256 frozen | `benchmarks/funnel_eval.py` | pre-registered funnel test |

## 5×100 labels (by construction, never from the system)
EQUIVALENT = same slots, different language/synonym/order · NOT_EQUIVALENT = exactly one slot changed (no negation flip) · PARTIALLY_EQUIVALENT = B = A + one extra slot ·
AMBIGUOUS = one text with a bare/vague referent · CONTRADICTORY = cannot both be obeyed (do/don't, enable/disable, allow/forbid, before/after).
Prediction mapping: [SEMANTIC_MODEL.md §Mapping](SEMANTIC_MODEL.md#mapping-to-the-six-statuses-of-22-derived-not-a-native-field). Also reports ambiguity false positives and silent-loss coverage.

## Metrics (what actually exists, `benchmarks/metrics.py`, `blind_eval.py`)
Equivalence accuracy / precision / recall / F1 / false-positive & false-negative rate · critical-drift detection rate · per-dimension preservation (negation, quantities, time, constraints,
conditions, references) and **full canonical round-trip** · per-category accuracy · latency per compare · 5-way class recall + confusion + by-language/kind · adversarial detection (not equivalent) and
critical-flag rate per attack family + control false-alarm rate. §44's other named metrics (semantic drift *rate* over a model chain, cross-lingual equivalence as its own metric)
are covered indirectly (the by-language breakdown) — not as separately named scalars.

## Current results (2026-10-02)
| Instrument | Result | Caveat |
|---|---|---|
| blind 1 / 2 / 3 / 4, rule-based, **fresh first runs** | 72 % / 80 % / 76 % / 76 % | the honest generalisation estimate (≈ 76–80 %) |
| blind 2 / 3 / 4, rule-based, today | 89.5 % / 81.0 % / 76.0 % | **contaminated** (sets 2–3 were read and fixed against); tracks regressions only |
| blind 9, LLM route (Sonnet) | 95.0 %, 39/39 critical drift | single run |
| 5×100 v1.2 | 497/500 = 99.4 % | same-author; v1 first run was 89.4 % (2 benchmark defects corrected, then 2 real system gaps closed) |
| security | 450/450 flagged; 54/57 hard critical; 0/31 false alarms | same-author; 3 declared limitations |
| **blind11, other author, run once** | rules 0.4: 50 % proven but 40.6 % false "equivalent"; AIXL LLM route: 0 % proven, 0.6 % false; **arbiter 2-of-2: 100 % proven, 0.6 % false** | Sonnet-authored; Haiku (not the author) matches Sonnet |
| **blind12, other authors, run once** | AIXL key recall 15.8 % (lexical baseline 60.3 %); arbiter 2-of-2 359/360 proven, 0/480 near-miss false | author-assigned cluster labels; disputes listed in ADR-017 |
Full tables and limits: [EVIDENCE.md](EVIDENCE.md), [adr/ADR-017.md](adr/ADR-017.md).

## Protocol for sets by other authors (2026-10-03)
Authors write without repository access and in domains disjoint from earlier sets; the file is validated, hashed (`*.sha256`) and committed; the arms, metrics and pass/fail gates are written into ADR-017 **before** any output exists ("PRE-REGISTRATION"); the set is evaluated once and then declared spent; disputed labels are listed, never silently changed. Two fixed arbiter rules (`data/blind10/arb_rules.txt`) are used by every arbiter run and were not tuned after seeing outputs.

## Reproducibility
Generators are seeded and tests assert the committed JSONL equals a regeneration. First-run result files in `BENCHMARK/` are read-only; `*_CONTAMINATED.json` are labelled as such.
Round trips: `tests/test_codec.py`; fingerprint/comparator agreement: `tests/test_fingerprint.py`.
Full per-round history and honest caveats: [../BENCHMARK.md](../BENCHMARK.md), [../BENCHMARK/PREREG_0.3.md](../BENCHMARK/PREREG_0.3.md).
