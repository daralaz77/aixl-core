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
