# blind17 (SHORT, 70 pairs) — pre-registration, written 2026-10-03 BEFORE the pairs exist
Purpose: verify the SAFETY fixes made after blind16 (he/she pronoun gender, explicit-vs-bare sequence order, plus related classes) and measure the HYBRID
(semantic veto + 2-of-2 arbiter) end to end. Code + arbiter rules frozen by hash in CODE_FREEZE.json; they MUST NOT change before the evaluation.
Authors: two fresh agents (Opus, Sonnet), 35 pairs each, no tools, nothing about AIXL; each pair carries a `family` tag of the trap it tests.
Judges for the arbiter arm: two fresh agents (Sonnet, Haiku), no tools, given ONLY data/arbiter/rules_v1.txt and the pairs (id, a, b) — never the labels or the semantic output.
Gates (written beforehand):
  S1 semantic false-equivalent <= 5% of non-EQUIVALENT-labelled pairs, AND zero false-equivalent in the families gender_pronoun and explicit_vs_bare_order.
  H1 hybrid false-SAME (verdict SAME on a pair not labelled EQUIVALENT, UNDECIDABLE included) <= 2%.
  H2 hybrid SAME on >= 85% of EQUIVALENT-labelled pairs.
  Reported, no gate: arbiter-alone false-SAME and SAME rate; semantic NOT_EQUIVALENT precision/recall; REVIEW count and its composition (true differences vs true equivalences = false vetoes).
Expectation written beforehand: S1 pass (the two safety classes are exactly those fixed after seeing blind16, so a miss there would be a real failure of the fix); H1 pass thanks to the
veto; H2 uncertain (35 EQUIVALENT-labelled pairs at most; any false veto lowers it). With 70 pairs and ~30 non-equivalent ones, 0 observed errors only bounds the true rate below ~10%; this is a verification
run, not a precision estimate.

## RESULT (run once on the FROZEN code + rules, 2026-10-03; raw output in RESULT_run1.txt; judge protocol in JUDGE_LOG.md) — set is now SPENT
Pairs: Opus X001-X035 + Sonnet Y001-Y035 = 70 (39 NOT_EQUIVALENT, 28 EQUIVALENT, 3 UNDECIDABLE). Judges: Sonnet + Haiku (2-of-2), each 70/70 valid answers.
The Haiku judge's two answer sets (markdown table, then pure TSV) are IDENTICAL on all 70 pairs (RESULT_run2_haiku_b.txt re-runs with the TSV): no judge instability here.
| gate | result | verdict |
|---|---|---|
| S1 semantic false-equivalent <= 5% AND zero in gender_pronoun / explicit_vs_bare_order | 2/42 = 4.8% numerically, but **1/10 in gender_pronoun (Y005 'his' vs 'her') and 1/7 in explicit_vs_bare_order (Y009)** | **FAIL** as pre-registered |
| H1 hybrid false-SAME <= 2% | **2/42 = 4.8%** (X024, Y009) | **FAIL** |
| H2 hybrid SAME on >= 85% of equivalent | 27/28 = 96.4% | PASS |
Reported: arbiter 2-of-2 alone: SAME on 28/28 equivalent, false-SAME 2/42 (the same X024, Y009) -> **the hybrid added no protection on this set**. Semantic NOT_EQUIVALENT precision 13/15 = 86.7%, recall 13/39 = 33%.
The semantic veto fired once (REVIEW) and was a FALSE veto (Y017 'está prohibido despegar sin autorización' vs 'es obligatorio contar con autorización': a wrong NOT_EQUIVALENT); it never caught a wrong SAME.
Breakdown of the 3 failures: Y005 = REAL DEFECT (English possessives his/her were gender-neutral; fixed after the run, test added). Y009 = label DISPUTED: both judges and the semantic model say 'ventilar después de fumigar' in both
texts; the author's NOT_EQUIVALENT label looks wrong, but it is counted as labelled and NOT changed. X024 'No es cierto que no debas cifrar' vs 'Debes cifrar': both judges said SAME, the semantic model was INCONCLUSIVE (it flags the double
negation under a modal as ambiguous) so it could not veto; the author's reading (negating a prohibition = permission, not obligation) is defensible.
Sample is tiny (42 non-equivalent pairs): 2 errors give a 4.8% point estimate with a 95% interval of roughly 0.6%-16%.
