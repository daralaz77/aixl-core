# blind16 — pre-registration (written 2026-10-03 BEFORE the pairs exist)
Judge for the second attempt at "reliable NOT_EQUIVALENT" (blind15 gave 80%, gate was 90%). Code frozen by hash in CODE_FREEZE.json; it MUST NOT change before the single
evaluation. Development sets (all seen, tuned on): golden_r, blind13, blind14, blind15. Authors: two fresh agents (Opus, Sonnet), no tools, nothing about AIXL.
Gates, identical to blind15 and written beforehand:
  G1 false-equivalent <= 5% | G2 PRECISION of NOT_EQUIVALENT >= 90% | G3 proven equivalent >= 70% (expected to FAIL).
Expectation written beforehand: G1 pass; G2 uncertain — dev sets show ~98% but they were tuned on, blind15 gave 80%, so the honest forecast is 80-92%; G3 fail.
Also reported: NOT_EQUIVALENT recall (~50% expected), INCONCLUSIVE rate, undecidable flagged. The sample of NOT_EQUIVALENT verdicts will again be only ~30-40, so
the 90% gate carries about +/-10-14 points of sampling error; a pass is "not rejected", not "proven".

## RESULT (run once, 2026-10-03, on the FROZEN code; raw output in RESULT_run1.txt) — set is now SPENT
Authors: Opus V001-V070, Sonnet W001-W070. 4 of 280 texts also appear in earlier sets (not removed).
| gate | result | verdict |
|---|---|---|
| G1 false-equivalent <= 5% | **2/82 = 2.4%** (V036, W045) | PASS, but NOT zero: the first non-zero false-equivalents in the project's independent sets |
| G2 NOT_EQUIVALENT precision >= 90% | **27/31 = 87.1%** | **FAIL** (blind15: 80%, blind14 before the fix: 55%) |
| G3 proven equivalent >= 70% | **1/58 = 1.7%** | FAIL (expected) |
NOT_EQUIVALENT recall 27/63 = 42.9%. INCONCLUSIVE 88/140; undecidable flagged 18/19.
The 2 false-equivalents: V036 'dale a él' vs 'dale a ella' (both pronouns resolved to the single candidate name, gender lost); W045 'y después reinicia' vs 'y reinicia' (explicit order vs bare 'and'
assumed equal). The 4 wrong NOT_EQUIVALENT: 'como máximo 40' vs 'ningún … más de 40' (each vs none), 'la primera' (anaphoric ordinal) vs the noun, 'solo se despacha' vs 'a menos que' (ONLY focus = 'se'),
'before shipping' vs 'prior to shipment'.
## AFTER the run (code changed, so this file's numbers are NOT re-measurable with the current code; the evaluator refuses to run on changed code)
All six classes were fixed with regression tests (tests/test_semantic_r.py). On the 5 development sets (golden_r, blind13-16, all seen and tuned on) NOT_EQUIVALENT precision is 160/162 and
false-equivalent 0 — that is development performance, not evidence. A fresh set (blind17) is required to know whether the fixes generalise.
