# AIXL 0.3-R golden set (v1, 2026-10-03)

`texts.jsonl` (110 texts) + `pairs.jsonl` (66 pairs: 36 NOT_EQUIVALENT, 21 EQUIVALENT, 9 UNDECIDABLE) across the ten
master-prompt categories (A negation, B quantity, C time, D condition, E scope/exception, F reference, H composition,
I ambiguity, J injection, K paraphrase/multilingual). Regenerate with `python -m benchmarks.golden_r_source`;
hashes in `MANIFEST.json` are checked by `tests/test_golden_r_dataset.py`. Score a system: `python -m benchmarks.golden_r_eval [--inconclusive] [--show]`.

## Labels
* EQUIVALENT / NOT_EQUIVALENT / **UNDECIDABLE** — undecidable = the text alone cannot prove either; the only safe answer is
  INCONCLUSIVE. Answering EQUIVALENT there is scored as a false-equivalent. NOT_EQUIVALENT is "over-decided" (neutral).
* `canonical_meaning` slots: action, polarity, object, actor, target, recipient, qty, time, cond, exception, sequence, ref,
  scope, modality, format, language, audience, length, source, unspecified. Value `UNSPECIFIED` means "the text does not say" (never a default).
* `forbidden_inferences`: slots a system must not fill in (e.g. audience/length for "Resume el informe.").

## What this set is NOT
* **Not independent.** Written by the same author as the system and while knowing its failures; labels are `author-assigned`,
  not human-reviewed. Use it as a regression/development set. Any accuracy claim needs a separately-authored, hash-frozen blind set.
* Small (66 pairs): per-category numbers are counts, not rates. ES-dominant (EN/PT only in A, K).
* Four labels were changed while authoring because they were genuinely undecidable (GP036 compare-order, GP038 'último',
  GP063 contrato/acuerdo, GP006 'no todos'); see REVIEW.md. One of them (compare-order) contradicts the label I gave A11 in the audit.
