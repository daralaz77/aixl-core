# Contributing to aixl-core

Thanks for looking. AIXL core is an experimental semantic comparator (ES / EN / PT) maintained by one person, so this page says exactly what is expected and what to expect back.

## Where to talk
- **Bugs, questions, ideas, proposed changes:** [GitHub Issues](https://github.com/daralaz77/aixl-core/issues) and pull requests (public, searchable, linkable by URL).
- **Security problems:** do **not** open an issue. Use GitHub's private vulnerability reporting or the address in [SECURITY.md](SECURITY.md).
- Language: English is preferred for issues and code comments; Spanish and Portuguese are welcome.

## How a change gets in
1. Open an issue first for anything larger than a typo, so we agree on the direction.
2. Fork, branch, make the change, open a pull request against `main`.
3. The pull request must pass the CI (`tests`, `lint`, `codeql`, the fuzz run). The maintainer reviews it; there is no second reviewer yet, so expect a note rather than a formal approval.
4. Releases are tagged `vX.Y.Z` and described in [CHANGELOG.md](CHANGELOG.md) and [docs/SEMANTIC_CHANGELOG.md](docs/SEMANTIC_CHANGELOG.md).

## Requirements for an acceptable change
- **Tests with the change.** New behaviour needs a test in `tests/` (an automated one, written on your own sentences, never copied from an evaluation set). A bug fix needs a regression test that fails before the fix.
- **No silent failure.** For the comparator, the project goal is that a changed meaning is never reported as EQUIVALENT. A change that raises a verdict from INCONCLUSIVE to EQUIVALENT needs evidence; one that lowers it does not.
- **Do not tune on the spent evaluation sets** (`data/blind*`). They are frozen with hashes and their pre-registration files say what each can and cannot show.
- **Lint clean:** `ruff check .` passes (config in `pyproject.toml`).
- **No new runtime dependency in the core.** The library has none (`dependencies = []`); optional extras are fine.
- **Dependencies are pinned by hash** (`requirements/*.in` → `pip-compile --generate-hashes`, see `requirements/README.md`); GitHub Actions are pinned by commit hash.

## Running the checks locally
```bash
python3 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements/ci.txt   # or: pip install pytest tiktoken hypothesis
.venv/bin/python -m pytest -q                      # the whole suite (about 1,900 tests, about a minute)
.venv/bin/python -m ruff check .                   # lint (pip install --require-hashes -r requirements/lint.txt)
AIXL_FUZZ_PROFILE=deep .venv/bin/python -m pytest tests/test_fuzz_properties.py   # longer property-based fuzzing, random seed
```
Mutation properties live in `tests/test_mutation_properties.py`: a new kind of meaning-changing edit is one more small function there.

## Code of conduct
Be kind and specific. Disagreement about a verdict is welcome when it comes with a sentence pair.
