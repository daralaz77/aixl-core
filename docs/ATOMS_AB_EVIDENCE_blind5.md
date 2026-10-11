# blind5 — A/B of the learned registry and of the normal form (pre-registration ADR-021)

Run 2026-10-10 under the hash freeze `data/atoms/FREEZE_blind5.json` (intact before and after; two evaluation runs byte-identical). Raw output: `data/atoms/RESULT_blind5.txt`.
Procedure exactly as pre-registered: 150 new texts (author Opus), four conditions on the same texts — P0 (curated registry only) and P1 (registry + the 93 learned concepts) × with / without the
normal form — two calls each (Sonnet, Opus), references = two independent annotators (Sonnet, Opus). 8 responses + 4 annotation files were produced by 12 separate subagents; all 12 files validated
(75 lines each, ids = batch ids, 0 duplicates, 0 parse errors) before evaluation.

## Result
| condition | valid S/O | pair exact | pair F1 | pair core | accept exact | accept core | accepted core F1 (vs refs) | collisions |
|---|---|---|---|---|---|---|---|---|
| P0 raw | 149/150 | 0.282 | 0.836 | 0.847 | 28.0% | 56.7% | 0.886 | 0 |
| P0 + normal form | 149/150 | 0.349 | 0.845 | 0.853 | 34.7% | 58.7% | 0.878 | 0 |
| P1 raw | 150/150 | 0.267 | 0.824 | 0.815 | 26.7% | 49.3% | 0.944 | 0 |
| P1 + normal form | 150/150 | 0.300 | 0.818 | 0.821 | 30.0% | 51.3% | 0.949 | 0 |

Paired flips on the 149 texts valid in all four calls (normalized exact agreement, Sonnet vs Opus): P1 agrees & P0 does not **16**; P0 agrees & P1 does not **23** (exact two-sided sign test, n = 39: p = 0.34).

| pre-registered hypothesis | verdict | numbers |
|---|---|---|
| H1 normal form (on P0): exact agreement ≥ +2 pts, core F1 drop ≤ 0.01 | **MET** | exact 0.282 → 0.349 (+6.7 pts); core 0.847 → 0.853 |
| H2 registry exposure: exact agreement ≥ +3 pts AND core acceptance ≥ +3 pts | **NOT MET** | exact 0.349 → 0.300 (**−4.9**); core acceptance 58.7% → 51.3% (**−7.4**) |
| H3 no harm: accepted core F1 P1 ≥ P0 − 0.02, collisions ≤ P0 + 1 | **MET** | 0.878 → 0.949; collisions 0 → 0 |
| H4 combined (P1 + normal form, `core`): acceptance ≥ 60% AND accepted core F1 ≥ 0.88 | **NOT MET** | acceptance 51.3% (F1 0.949 passes, acceptance fails) |

## What follows under the pre-registered rule ("a failed hypothesis is reported as failed and the corresponding claim is withdrawn")
- **Withdrawn:** "exposing the 93 learned concepts raises Sonnet–Opus agreement and acceptance" (H2). The measured direction is the opposite: agreement −4.9 pts and acceptance −7.4 pts. The paired flips (16 vs 23, p = 0.34)
  do not prove harm at n = 150, so the honest wording is **no benefit detected; the point estimate is negative**.
- **Withdrawn:** "the combined pipeline reaches ≥ 60% acceptance" (H4): 51.3%.
- **Supported:** the normal form increases exact Sonnet–Opus agreement on the curated registry (H1), by +6.7 pts, well above the ≈ ±3–4 pt noise the pre-registration declared, with core F1 not lowered.
  Under P1 the same direction holds (+3.3 pts exact, +2.0 pts acceptance) but was not a pre-registered hypothesis.
- **Not evidence of improvement, despite "MET":** H3. Accepted core F1 is higher under P1 (0.949 vs 0.878) but P1 accepts fewer texts (51.3% vs 58.7%); a smaller, easier accepted subset naturally scores higher.
  H3 only certifies that no harm was detected on that subset and that there were no fingerprint collisions.

## Reading the numbers
- Absolute agreement is low: Sonnet and Opus produce exactly the same normalized graph on 30–35% of the texts, and core-level acceptance never exceeds 59%. This matches the earlier finding that open-text label stability, not the extractor, is the ceiling.
- P1 gives 150/150 valid parses against 149/150 for P0 on one side (one response line failed validation under P0); that difference is too small to interpret.
- 0 different-text fingerprint collisions among accepted graphs in all four conditions.

## Limits of this evidence
- n = 150 texts by one author (Opus); one run per cell; two models. The declared noise floor is ≈ ±3–4 pts.
- Independence of the 12 subagents was enforced by written instruction only (no technical sandbox). Tool-use counts are consistent with the instructions (responders: 2 reads + 1 write; annotators 6–9 reads/writes) but cannot prove it.
- The annotators read the repository, including the learned registry, as the pre-registration says; the references are therefore not independent of the registry the P1 condition exposes.
- Between the pre-registration commit and this run the code text of `aixl/atoms/` and `aixl/semantic/` was edited by a behaviour-neutral cleanup; equivalence was measured (1,648/1,648 extractions, 4/4 prompts, 8/8 responses identical) and recorded in the ADR-021 addendum.
- Not tested: other authors, other languages mixes, other model pairs, P1 with a different promotion rule.

## Reproduce
`python benchmarks/atoms_ab_eval.py` (refuses to run if any file in the freeze changed; exit code 2 lists what is missing).
