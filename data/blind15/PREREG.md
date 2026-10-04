# blind15 — pre-registration (written 2026-10-03 BEFORE the pairs exist)
Judge for the "reliable NOT_EQUIVALENT" work on aixl/semantic. Code frozen by hash in CODE_FREEZE.json before the authors are asked;
it MUST NOT change before the single evaluation. Development sets: golden_r, blind13, blind14 (all seen; blind14 error analysis drove the changes).
Authors: two fresh agents (Opus, Sonnet), no tools, nothing about AIXL. Labels are the authors' own.
Gates written beforehand:
  G1 false-equivalent <= 5% of pairs not labelled EQUIVALENT                      (carried over)
  G2 PRECISION of NOT_EQUIVALENT >= 90%: of all NOT_EQUIVALENT verdicts, the share whose label is NOT_EQUIVALENT   (new; blind14-before-fix was 55%)
  G3 proven equivalent >= 70%                                                        (expected to FAIL; dev showed 2/55)
Also reported: NOT_EQUIVALENT recall (labelled-different pairs the system proves different), INCONCLUSIVE rate, undecidable flagged.
Expectation written beforehand: G1 pass, G2 borderline-pass, G3 fail; NOT_EQUIVALENT recall will be roughly half.

## RESULT (run once, 2026-10-03; code hash verified unchanged; raw output in RESULT_run1.txt) — set is now SPENT
Authors: Opus R001-R070, Sonnet T001-T070; 0 of 280 texts overlap earlier sets.
| gate | result | verdict |
|---|---|---|
| G1 false-equivalent <= 5% | **0/77 = 0.0%** (Opus 0/39, Sonnet 0/38) | PASS |
| G2 NOT_EQUIVALENT precision >= 90% | **28/35 = 80.0%** | **FAIL** (blind14 before the fix: 39/71 = 55%) |
| G3 proven equivalent >= 70% | **1/63 = 1.6%** | FAIL (expected) |
NOT_EQUIVALENT recall 28/58 = 48.3%. INCONCLUSIVE 89/140; undecidable flagged 15/19. The 7 wrong NOT_EQUIVALENT: 4 are UNDECIDABLE-labelled pairs (bimensual, "cada semana" vs "al final de la semana",
modifier scope "vehículos y motos menores de…", "older customers"), 3 are true paraphrases (except/exempt, PT "caso", "antes de X, Y" vs "Y; solo después, X").
