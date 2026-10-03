# Versioning policy

`MAJOR.MINOR.PATCH` (package `aixl`, `aixl.__version__`; the wire version token is `AIXL-<MAJOR>.<MINOR>`, currently `AIXL-0.3`). While MAJOR is 0 the project is experimental and may change; the rules below still apply and every change is documented.

| Change | Bump | Examples |
|---|---|---|
| Changes the meaning of an existing token or atom, removes/renames an atom, changes the canonical form so previously-equal meanings differ (or vice versa), changes a default severity from non-CRITICAL to CRITICAL or back | **MAJOR** (or MINOR while 0.x, with a loud entry in the changelog) | redefine `F:`; move `SCOPE` from constraints to its own atom |
| New compatible capability | **MINOR** | new action verb, noun, unit, constraint key, warning type, CLI command, API function |
| Fix that makes behaviour match the documented/intended meaning, vocabulary additions that only reduce silent loss, docs | **PATCH** | new negation cue (`Avoid …`), PT lexicon entries, `sanitize_input` |

Current: package **0.5.0**, wire token `AIXL-0.3` (unchanged; `R:` is additive). Scope of 0.5: [adr/ADR-018.md](adr/ADR-018.md).

## What is stable
* The wire format and atom meanings of a given `V:` version (PROTOCOL.md).
* Result **shapes** (`ComparisonResult.to_dict()` keys, `AixlError.code`) within a MINOR line; keys are only added (`warnings` appears only when non-empty).
* `data/config.json` keys (weights, severities, `destructive_actions`, `irreversible_actions`, `critical_constraint_keys`).

## What is deliberately NOT stable
* **Fingerprints** are a function of the canonical form, the lexicon and the reference date. A vocabulary or normalization change can change a fingerprint. Store `aixl.__version__` next to any persisted fingerprint
  and only compare fingerprints produced by the same version and `today`.
* Rule-based accuracy on fresh data (it moves with the lexicon).
* The experimental `similarity` score.

## Compatibility
Parser reads `AIXL-0.2` and `AIXL-0.3`; everything else is `VERSION_MISMATCH` (explicit, never a silent downgrade). When a newer message carries a construct an older reader cannot represent, the intended behaviour is
`UNSUPPORTED_CAPABILITY` — a capability handshake is not built yet ([INTEROPERABILITY_GUIDE.md](INTEROPERABILITY_GUIDE.md)).

## Release checklist
1. `pytest -q` green on Python 3.11 and 3.12. 2. Ratchets (`test_sil5x100`, `test_sil_security`) and blind sets 1–4 unchanged or improved on purpose. 3. `tests/test_docs.py` green.
4. Any semantic change has a regression test (`test_bugNNN`) **and** a note in `LIMITATIONS.md`/`BENCHMARK.md` with before/after numbers. 5. Never change the semantics of an existing token without documenting it in the same commit.
