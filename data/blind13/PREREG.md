# blind13 — pre-registration (written 2026-10-03, BEFORE any system was run on these files)
Authors: Opus (O001-O070) and Sonnet (S001-S070), each told to use no tools and given nothing about AIXL or its golden set
(enforced only by the prompt; each agent made one tool call, the hand-back). Labels are the authors' own; no human review.
Files are hash-frozen in MANIFEST.json. Evaluation is run ONCE; afterwards the set is SPENT (no tuning on it).
Arms: rules route (inconclusive OFF), rules route (inconclusive ON). Scoring as in benchmarks/golden_r_eval.py.
Gates (same as blind11): false-equivalent <= 5% of pairs whose label is not EQUIVALENT; proven-equivalent >= 70% of EQUIVALENT pairs.
Reported separately per author (author disagreement is itself a result) and per category. Label disagreements with data/golden_r
(e.g. compare-order S036 vs GP036) are reported, never "fixed".

## RESULT (run once, 2026-10-03) — set is now SPENT; raw output in RESULT_run1.txt
| arm | false-equivalent (gate <=5%) | proven equivalent (gate >=70%) | undecidable flagged |
|---|---|---|---|
| rules, inconclusive OFF | 47/89 = 52.8% | 19/51 = 37.3% | 0/18 |
| rules, inconclusive ON | 18/89 = 20.2% | 4/51 = 7.8% | 3/18 |
Both arms FAIL both gates. Per author (OFF): Sonnet 55.3% / 39.1%, Opus 50.0% / 35.7%. 32 false rejects of true equivalents in both arms.
The author-written golden_r predicted this well (55.6% / 24.4% on its own 66 pairs) — it was a fair development proxy.
