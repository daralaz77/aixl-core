# blind14 — pre-registration (written 2026-10-03 BEFORE the pairs exist)
Judge for the 0.3-R semantic track (aixl/semantic). Code frozen by hash in CODE_FREEZE.json before authors are asked; the code
MUST NOT change between freezing and the one evaluation. Development sets for this track: golden_r and blind13 (both seen).
Authors: two fresh agents (Opus, Sonnet) told to use no tools and given nothing about AIXL; labels are the authors' own.
Gates (same as blind11/13): false-equivalent <= 5% of non-EQUIVALENT-labelled pairs; proven equivalent >= 70% of EQUIVALENT pairs.
Report both, plus INCONCLUSIVE rate, false rejects (NOT_EQUIVALENT on a true paraphrase) and over-decisions. Expectation written
beforehand: the false-equivalent gate may pass; the proven >=70% gate is expected to FAIL (blind13-as-dev showed 7/51).

## RESULT (run once, 2026-10-03; code hash verified unchanged; raw output in RESULT_run1.txt) — set is now SPENT
Authors: Opus P001-P070, Sonnet Q001-Q070 (one text, "Only managers can approve expenses.", also appears in blind13 — 1 of 280 texts).
| gate | result | verdict |
|---|---|---|
| false-equivalent <= 5% | **0/85 = 0.0%** (Opus 0/42, Sonnet 0/43) | PASS |
| proven equivalent >= 70% | **0/55 = 0.0%** | FAIL (expected beforehand) |
Other: undecidable flagged 11/20; INCONCLUSIVE 58; false rejects 23 (NOT_EQUIVALENT on true paraphrases); over-decided 9.
