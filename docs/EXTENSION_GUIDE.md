# Extension guide

Design intent (§38): **CORE + EXTENSIONS** — universal concepts in the core, domain vocabulary (finance, health, robotics, legal…) in extensions. Reality check: there is **no extension registry** yet (§52 is design-only).
Today an extension is a small Python module that appends to the closed lexicons at import time. This guide shows exactly that, and the test that proves it works.

## Before adding anything (§59)
Is it semantic, syntactic, transport, adaptation, or domain-specific? Provider-specific ⇒ never in `core`. Domain-specific ⇒ extension module, not an edit of the shared lists. Remember that
out-of-lexicon words are *reported*, not lost silently: the `UNRECOGNIZED_TERMS` warning tells you which nouns need an entry.

## Recipes
| You add | Where | Notes |
|---|---|---|
| a noun (object) | `ENTITY_RX` or `DATA_RX` in `aixl/legacy02/translators/natural_to_semantic.py`, plus `ENTITIES`/`DATA` in `aixl/core/ontology.py` | regex runs on **accent-stripped lowercase** text; include ES/EN/PT forms; also set `NOUN_CANON[NAME] = NAME` if you append at runtime |
| an action verb synonym | `EXTRA_ACTION_RX` in `aixl/core/normalizer.py` (or `ACTION_RX` in the 0.2 analyzer) | regex over accent-stripped text; a word preceded by an article is not treated as a verb |
| a *new* canonical action | the verb above **and** `ACTIONS` + `ACTION_TO_INTENT` in `aixl/legacy02/protocol/atoms.py`; decide if it belongs in `destructive_actions` / `irreversible_actions` | changes meaning of the vocabulary ⇒ MINOR bump |
| a unit | `UNIT_MAP` in `aixl/core/normalizer.py` | |
| a constraint key | emit `KEY=VALUE` into `frame.constraints` in the translator; if loss of it is safety-relevant add it to `critical_constraint_keys` in `data/config.json` | e.g. `SCOPE` |
| a severity / weight | `data/config.json` | configuration, not code |

## Worked example — domain extension for invoices (verified by `tests/test_docs.py`)
Without it, "Generate the invoice" silently drops the object and raises `UNRECOGNIZED_TERMS`. As a standalone module `finance_ext.py`:
```python
from aixl.legacy02.translators import natural_to_semantic as L

def install():
    L.ENTITY_RX.append(("INVOICE", r"\b(facturas?|invoices?|faturas?)\b"))
    L.NOUN_CANON["INVOICE"] = "INVOICE"
```
After `install()`: `compare("Generate the invoice today.", "Generate the report today.")` reports `ENTITIES: INVOICE → REPORT` and no `UNRECOGNIZED_TERMS`;
`compare("Genera la factura hoy.", "Generate the invoice today.")` is equivalent. (The module must be imported before the first translation; `lru_cache`d lexicon helpers read the lists lazily.)

## Checklist for every extension
1. A failing test first (`tests/test_regression.py::test_bugNNN` for core changes, or your own file for an extension module).
2. Whole suite + ratchets + blind sets 1–4 unchanged unless intended ([DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)).
3. Re-measure semantic drift: add the new words to a minimal-pair test (the new noun must make two *different* instructions non-equivalent).
4. Version bump per [VERSIONING_POLICY.md](VERSIONING_POLICY.md) (new vocabulary = MINOR or PATCH; changed meaning = MAJOR).
5. Document the entry (which domain, which words, who owns it).
