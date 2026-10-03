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

## Reproducibility
Generators are seeded and tests assert the committed JSONL equals a regeneration. First-run result files in `BENCHMARK/` are read-only; `*_CONTAMINATED.json` are labelled as such.
Round trips: `tests/test_codec.py`; fingerprint/comparator agreement: `tests/test_fingerprint.py`.
Full per-round history and honest caveats: [../BENCHMARK.md](../BENCHMARK.md), [../BENCHMARK/PREREG_0.3.md](../BENCHMARK/PREREG_0.3.md).
