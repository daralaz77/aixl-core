# Changelog

Human-readable summary of what changes between releases. The detailed, per-change compatibility tables (backward compatibility, migration, test impact) are in [docs/SEMANTIC_CHANGELOG.md](docs/SEMANTIC_CHANGELOG.md); the project history is in [docs/HISTORY.md](docs/HISTORY.md). Version numbers follow [Semantic Versioning](https://semver.org/) (see `docs/VERSIONING_POLICY.md`); while the major version is 0, a MINOR bump may change the canonical form.

## 0.7.0 — 2026-11-11
Strict hybrid, three comparator changes, and the evidence behind them. The wire token stays `V:AIXL-0.3`. Comparator verdicts change in a few pairs (see Comparator below), so this is a MINOR bump (`docs/VERSIONING_POLICY.md`).
### Added
- Strict hybrid: `aixl.semantic.hybrid_decide(..., require_semantic_equivalent=True)`, `hybrid_protocol.decide(..., strict=True)` and the MCP tool `aixl_hybrid_decide(..., strict=True)`. A unanimous judge SAME is accepted only if the rule-based comparator also proves EQUIVALENT; otherwise REVIEW. Default behaviour is unchanged. Measured evidence and its limits: `docs/HYBRID_MCP.md`.
- Evidence sets `data/blind26` (80 model-written pairs, new families) and `data/blind27` (100 human-labelled pairs from PAWS-X and CondaQA; references only, no third-party text), each pre-registered and run once.
- Evidence sets `data/blind28` (120 in-vocabulary pairs, three judges including a local non-Claude model) and `data/blind29` (120 fresh pairs, paired old-versus-new comparison).

### Comparator
- Fixed deadline phrasings are now proven equal: 'no later than X' = 'by X', 'by X at the latest' = 'by X', 'no máximo até' = 'até', 'no después del' = 'hasta el'. A bare 'at the latest' stays content. Applied after the strict-mode token identity, so strict mode still reads the words as written.
- A fronted time or frequency adjunct is moved to the end ('After C, do A' = 'Do A after C', 'Mañana, X', 'Cada semana, X', 'Every Monday, X'); 'before' and 'after' stay distinct.
- 'never / nunca / jamás' and 'qualquer / cualquier' on one side only now make EQUIVALENT impossible (INCONCLUSIVE).
- Measured on 120 fresh pairs (blind29, same pairs through the old and the new comparator): false accepts 2 -> 1 of 60 (none new), proven equivalents 29 -> 31 of 60 (3 gained, 1 lost; the pre-registered rule asked for +5 and does NOT hold). The gain is in the deadline construct (0/6 -> 3/6); the fronted-adjunct rule did not fire on any fresh pair. In-distribution constructs, model authors, small sample: not a generalisation claim.

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
