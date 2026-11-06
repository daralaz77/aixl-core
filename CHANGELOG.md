# Changelog

Human-readable summary of what changes between releases. The detailed, per-change compatibility tables (backward compatibility, migration, test impact) are in [docs/SEMANTIC_CHANGELOG.md](docs/SEMANTIC_CHANGELOG.md); the project history is in [docs/HISTORY.md](docs/HISTORY.md). Version numbers follow [Semantic Versioning](https://semver.org/) (see `docs/VERSIONING_POLICY.md`); while the major version is 0, a MINOR bump may change the canonical form.

## 0.6.0 — 2026-11-06
### Security
- Private vulnerability reporting, Dependabot, secret scanning and push protection enabled; `SECURITY.md` and `.well-known/security.txt` updated.
- CodeQL, OpenSSF Scorecard and ClusterFuzzLite (Atheris) run in CI; every GitHub Action, the base images and the Python dependencies are pinned by hash.
- Fixed a denial of service: `to_semantic` took 19 s on 2,000 digits (cubic regular expression) and a 16,000-digit number raised `ValueError`; both now finish in under a second.
- `docker-publish` runs only for pushes to this repository's own `main`.
- No known vulnerability is open. No CVE has been assigned to any issue fixed in this version.

### Comparator
- Closed list of difference types that may assert NOT_EQUIVALENT; unreliable ones are kept as `Verdict.suspected`.
- Dropped-feature ledger: plural, indefinite article, past/future marker and version-like numerals can no longer be silently folded away by EQUIVALENT.
- New strict mode: `compare_texts(a, b, strict=True)`, MCP tool `aixl_compare_semantic`, CLI `semantic --strict` (EQUIVALENT only for the same token sequence).
- Fixed 10 silent-failure holes found by outside-author evaluation sets (blind19–25) and by mutation properties.

### Added
- Mutation property tests, Hypothesis fuzzing, SBOM generation (`scripts/make_sbom.py`), `CONTRIBUTING.md`, security documentation (`docs/THIRD_PARTY.md`, `docs/INCIDENT_RESPONSE.md`, `docs/SECURITY_MILESTONES.md`).

## 0.5.0 — 2026-10-03
Additive and opt-in changes; the wire token stays `V:AIXL-0.3`. Verdict field (EQUIVALENT / NOT_EQUIVALENT / INCONCLUSIVE), residue dimension, completeness check, the 2-of-2 arbiter. Details: [docs/SEMANTIC_CHANGELOG.md](docs/SEMANTIC_CHANGELOG.md).

## 0.4.0 — 2026-10-02
Canonical form gains a dimension (ordering constraint, action-argument bindings, node provenance); `validate()` and `round_trip()` added. Details: [docs/SEMANTIC_CHANGELOG.md](docs/SEMANTIC_CHANGELOG.md).
