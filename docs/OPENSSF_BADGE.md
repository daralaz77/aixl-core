# OpenSSF Best Practices badge: answers for the "passing" level

Prepared 2026-11-06 from the repository itself, for the form at <https://www.bestpractices.dev/en/projects/new> (project URL: `https://github.com/daralaz77/aixl-core`). Criteria: <https://www.bestpractices.dev/en/criteria/0>. Each row says what to answer and the URL or one-line justification to paste. **Rows marked ATTEST are statements only the maintainer can make; rows marked TODO need something done first.** Replace `main` URLs once the files below are pushed.

Base: `R = https://github.com/daralaz77/aixl-core`, `B = R/blob/main`.

## Basics
| Criterion | Answer | URL / justification |
|---|---|---|
| description_good | Met | `B/README.md` (what the library does and, at the top, what it does NOT prove) |
| interact | Met | `B/README.md`, `B/CONTRIBUTING.md` (obtain: git clone / Docker image; feedback: Issues; contribute: pull requests) |
| contribution | Met | `B/CONTRIBUTING.md` |
| contribution_requirements | Met | `B/CONTRIBUTING.md` ("Requirements for an acceptable change") |
| floss_license | Met | MIT, `B/LICENSE` |
| floss_license_osi | Met | MIT is OSI-approved |
| license_location | Met | `B/LICENSE` |
| documentation_basics | Met | `B/README.md`, `B/docs/DEVELOPER_GUIDE.md` |
| documentation_interface | Met | `B/docs/API_REFERENCE.md`, `B/docs/CLI_REFERENCE.md` |
| sites_https | Met | GitHub and ghcr.io are HTTPS only. The repository has no separate project website; the GitHub page is the site |
| discussion | Met | GitHub Issues and pull requests: searchable, addressable by URL, open to anyone with a GitHub account |
| english | Met | documentation and code comments are in English (ES/PT only in test data and some notes) |
| maintained | Met | commits on most days since 2026-09-29; see `R/commits/main` |

## Change control
| Criterion | Answer | URL / justification |
|---|---|---|
| repo_public | Met | `R` |
| repo_track | Met | git history: who, what, when |
| repo_interim | Met | every commit is public on `main`, not only releases |
| repo_distributed | Met | git |
| version_unique | Met | tag `v0.6.0` (`R/releases/tag/v0.6.0`); version in `pyproject.toml` and `aixl.__version__` |
| version_semver | Met | `B/docs/VERSIONING_POLICY.md` (SemVer) |
| version_tags | Met | git tags `v0.6.0` and `v1.0.0-paper` |
| release_notes | Met | the notes of the GitHub release `v0.6.0`, `B/CHANGELOG.md` and `B/docs/SEMANTIC_CHANGELOG.md` |
| release_notes_vulns | Met (N/A-like) | `B/CHANGELOG.md` states that no CVE has been assigned to any fixed issue in the version |

## Reporting
| Criterion | Answer | URL / justification |
|---|---|---|
| report_process | Met | `R/issues` and `B/CONTRIBUTING.md` |
| report_tracker | Met | GitHub Issues |
| report_responses | Met | no bug reports have been filed yet, so none is unanswered. Re-check this answer if reports arrive |
| enhancement_responses | Met | same: no requests so far |
| report_archive | Met | `R/issues?q=is%3Aissue` (public, searchable) |
| vulnerability_report_process | Met | `B/SECURITY.md` and `B/.well-known/security.txt` |
| vulnerability_report_private | Met | GitHub private vulnerability reporting (`R/security/advisories/new`) and the email in `B/SECURITY.md` |
| vulnerability_report_response | N/A | no vulnerability reports received in the last 6 months. `B/SECURITY.md` promises acknowledgement within 5 working days |

## Quality
| Criterion | Answer | URL / justification |
|---|---|---|
| build | Met | `python -m build --wheel` (the `wheel` job in `B/.github/workflows/tests.yml`) and `B/Dockerfile` |
| build_common_tools | Met | setuptools, pip, Docker |
| build_floss_tools | Met | all tools are FLOSS |
| test | Met | pytest suite in `B/tests` (about 1,900 tests), released under MIT; run with `python -m pytest -q` (`B/CONTRIBUTING.md`, `B/README.md`) |
| test_invocation | Met | standard `pytest` |
| test_most | Met | unit, regression, mutation-property, Hypothesis fuzz and Atheris fuzz tests; coverage is not measured with a tool, so do not claim a percentage |
| test_continuous_integration | Met | `B/.github/workflows/tests.yml` |
| test_policy | Met | `B/CONTRIBUTING.md` ("Tests with the change") |
| tests_are_added | Met | the recent changes each added tests: see `R/commits/main` (for example the mutation, ReDoS-budget and strict-mode tests) |
| tests_documented_added | Met | `B/CONTRIBUTING.md` |
| warnings | Met | ruff linter in CI (`lint` job) |
| warnings_fixed | Met | `ruff check .` passes on `main` |
| warnings_strict | Met | ruff configured in `pyproject.toml` (bug-finding rule sets such as B and F enabled) |

## Security
| Criterion | Answer | URL / justification |
|---|---|---|
| know_secure_design | **ATTEST** | only you can state this. Supporting evidence: `B/docs/SECURITY_MODEL.md`, the fail-closed design, `B/SECURITY.md` ("What the code does to protect a deployment") |
| know_common_errors | **ATTEST** | same. Supporting evidence: ReDoS found and fixed (`B/tests/test_redos_budget.py`), input caps, no shell execution of user text |
| crypto_published | Met | only Ed25519 and SHA-256, through the `cryptography` library (`B/aixl/signed_envelope.py`) |
| crypto_call | Met | uses `cryptography`, not hand-written primitives |
| crypto_floss | Met | the `cryptography` library is FLOSS |
| crypto_keylength | Met | Ed25519 (about 128-bit security) and SHA-256 |
| crypto_working | Met | no MD5, SHA-1, DES or RC4 anywhere in `aixl/` (searched) |
| crypto_weaknesses | Met | same search |
| crypto_pfs | N/A | the project implements no key agreement protocol |
| crypto_password_storage | N/A | the project stores no passwords |
| crypto_random | Met | nonces from `os.urandom` (`B/aixl/signed_envelope.py`) |
| delivery_mitm | Met | GitHub over HTTPS; image on ghcr.io over HTTPS |
| delivery_unsigned | Met | no hash is fetched over HTTP; dependencies are pinned by hash (`B/requirements/README.md`) |
| vulnerabilities_fixed_60_days | Met | no open Dependabot alerts; no open vulnerability report (checked 2026-11-06) |
| vulnerabilities_critical_fixed | Met | the one exploitable issue found (cubic regex) was fixed the same day (`R/commits/main`, `B/tests/test_redos_budget.py`) |
| no_leaked_credentials | Met | secret scanning and push protection are enabled; no credentials in the repository |

## Analysis
| Criterion | Answer | URL / justification |
|---|---|---|
| static_analysis | Met | CodeQL (`B/.github/workflows/codeql.yml`) plus ruff |
| static_analysis_common_vulnerabilities | Met | CodeQL's security queries |
| static_analysis_fixed | Met | the 15 ReDoS alerts were measured, one exploitable pattern fixed, the rest dismissed with a written reason (alert comments) |
| static_analysis_often | Met | every push, every pull request and weekly |
| dynamic_analysis | Met | Hypothesis property tests and Atheris fuzzing (`B/fuzz`, `B/.github/workflows/cflite.yml`) |
| dynamic_analysis_unsafe | N/A | pure Python, no memory-unsafe code |
| dynamic_analysis_enable_assertions | Met | the fuzz harnesses assert the project invariants on every input (`B/fuzz/fuzz_semantic.py`) |
| dynamic_analysis_fixed | Met | nothing found by the fuzzers so far (150 s runs and 2 deep Hypothesis runs); would be fixed |

## Before you submit (what I could not do for you)
1. ~~Create a release tag~~ Done 2026-11-06: `v0.6.0` is published and marked Latest; the three version rows above are Met.
2. **Answer the two ATTEST rows** honestly. If you do not yet feel able to, answer "Unmet" and explain; a project can still earn the badge by meeting the others later.
3. Create the project entry while signed in with GitHub on bestpractices.dev (it reads the repository for you), then paste the answers above. I cannot sign in for you.
4. After the badge exists, add its markdown to the README and re-run the Scorecard workflow; the alert closes on its next pass.
