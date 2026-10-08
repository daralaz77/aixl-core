# Pre-registration — normal form + learned registry, A/B on blind5 (written 2026-10-05 BEFORE any blind5 text, call or annotation exists)

State being tested (commit of this file): graph normal form v0.2 (lemma, 21 judged aliases, compound collapse, unit aliases) and registry 0.4.0 with 93 learned concepts (promote rule: ≥ 3 dev texts, each by ≥ 2 independent sources; mined from blind1v3+blind2+blind3 only). Offline, on the held-out blind4 (never mined), the normal form raised pairwise exact-graph agreement 0.365 → 0.393 with F1 0.839 → 0.839 and core F1 0.823 → 0.822.
Design: 150 NEW texts (author Opus), identical guide. Four conditions on the SAME texts, two calls each (Sonnet, Opus):
* P0 prompt = curated registry only (learned concepts hidden); P1 prompt = registry with the 93 learned concepts exposed (`build_prompt(learned=False/True)`).
* Each condition read with and without the normal form. References for quality: two independent annotators (Sonnet, Opus) who read the repo (registry 0.4.0); all graphs and references are normalized when quality is reported.
Hypotheses (declared success criteria):
* H1 normal form: on P0, normalization raises Sonnet-vs-Opus exact agreement by ≥ +2 points absolute and does not lower core F1 by more than 0.01.
* H2 registry exposure: under normalization, P1 raises Sonnet-vs-Opus exact agreement over P0 by ≥ +3 points AND raises `core` acceptance by ≥ +3 points (paired on the same texts; report the counts of texts that flip each way; the noise at n = 150 is ≈ ±3-4 points, so a smaller difference is "not detected").
* H3 no harm: accepted-subset core F1 against the references under P1 is not lower than under P0 by more than 0.02; different-text fingerprint collisions among accepted graphs ≤ P0 + 1.
* H4 combined pipeline (P1 + normal form, policy `core`): acceptance ≥ 60 % and accepted core F1 ≥ 0.88.
Rule fixed in advance: a failed hypothesis is reported as failed and the corresponding claim is withdrawn ("not detected"). No code, guide, prompt or table changes between this commit and the blind5 results.

## Addendum 2026-10-08 — maintenance commits after the freeze, equivalence evidence, and the hash freeze (written BEFORE any blind5 response or annotation exists)
**What happened.** After this pre-registration commit (`d2481f1`, 2026-10-05) a repository-wide cleanup (`docs/CLEANUP_ROADMAP.md`, phases 0–6) edited the text of 7 files under `aixl/atoms/`
(import order, unused imports/variables, removal of branches that could never execute in `extract.py`, a new `aixl/atoms/__init__.py` carrying a status banner) and several files under
`aixl/semantic/` (the package atoms imports). The rule above ("no code ... changes between this commit and the blind5 results") was therefore not respected at the level of file text.

**Evidence that behaviour did not change**, measured with `benchmarks/atoms_equiv_probe.py` (code of `d2481f1` in a worktree vs HEAD, identical inputs from `data/atoms/`):
the 4 blind5 prompts regenerated with `build_prompt` are 4/4 identical to each other and byte-for-byte identical to the stored `prompt_blind5_P{0,1}_b{1,2}.txt`;
the rule extractor plus normal form on 1,648 texts: 1,648/1,648 identical (graph fingerprint, normalised fingerprint and full graph); the 8 stored earlier model responses
parsed and normalised: 8/8 identical. Not covered: inputs outside those 1,648 texts.

**Decision.** The experiment is not invalidated by this, but the claim is recorded instead of hidden. To prevent any further drift the state under test is now FROZEN by hash:
`data/atoms/FREEZE_blind5.json` (30 files: `aixl/atoms/*.py` and `aixl/atoms/data/*.json`, `aixl/semantic/*.py`, `docs/ATOM_MODEL.md`, the four evaluation scripts including `atoms_ab_eval.py` and the freeze tool itself,
the 150 cases, the two batches and the four prompts), written by `benchmarks/atoms_freeze.py`. `atoms_ab_eval.py` now verifies it first and exits with code 2 if anything changed ("blind5 is VOID"),
and it reports exactly which of the 8 response files and the reference annotations are still missing instead of failing with a TypeError. Consequence: any later edit to those files (including a
cleanup of `aixl/semantic/`) voids blind5 until the results are produced; run blind5 first, clean afterwards.
