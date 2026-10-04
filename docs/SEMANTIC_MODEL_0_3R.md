# AIXL 0.3-R — Semantic Model (step 2 of the rebuild)

Code: `aixl/semantic/` (`model.py`, `lexicon.py`, `parser.py`, `compare.py`). It runs **in parallel** with the 0.3-0.5 core; `aixl.compare` is unchanged.
Scope (decision of 2026-10-03, Option 1): a **bounded controlled domain** — imperative / rule-style instructions in ES, EN, PT — with
`INCONCLUSIVE` as the answer for everything outside it. It is not an open-text meaning engine (docs/EVIDENCE.md still applies to open text).

## What changed versus 0.3-0.5 (root causes P1-P4 of the audit)
| Problem | Old behaviour | 0.3-R |
|---|---|---|
| P1 scope / exception lost | fixed-slot frame; no slot => silently dropped | every content token is kept as an ordered `item`; scope-bearing constructs (`EXCEPT`, `ONLY`, `WITHOUT`, `COND`, `QUANT`) are typed atoms |
| P2 time / order / ordinals flattened | `before` / `at` / `after` collapsed to one value | `TIME(rel, value)` with relation; ordered `steps` with `order = explicit / implicit`; positional `ORD` atoms |
| P3 no fail-closed default | `EQUIVALENT` unless something differed | `EQUIVALENT` only when **every** slot is equal and nothing is open; else `INCONCLUSIVE` with reasons |
| P4 explicit vs inferred lost | normalizer overwrote provenance | each atom has `provenance` (EXPLICIT / INFERRED / DEFAULTED); resolved clitics are INFERRED; bare numbers are DEFAULTED-exact |

## Model
* **Atom** = `type, value, span, provenance, scope(step), confidence, candidates`. `candidates` non-empty **is** the AMBIGUOUS state:
  the parser records the other readings instead of choosing one. Examples: `evita X` = `DISCOURAGE` with candidate `DONT`; `último` = `last`
  with candidate `most_recent`; `antes del viernes` = `before` with candidate `until` (inclusive limit); `no … todos` = `not_all` with candidate `any`.
* **Atom types**: `ACTION, DEONTIC (DO / DONT / MAY / DISCOURAGE / ADVISE / NOT_REQUIRED), QTY (mode, value, unit), QUANT (all / some / each / any / not_all), TIME, COND (kind suff|nec, negated, bag),
  EXCEPT, WITHOUT, ONLY, ORD, RECIPIENT, REF`. Absence of an atom type = the text does not say (`UNSPECIFIED`); it is never defaulted.
* **Step** = one action with its atoms and ordered `items`. Steps come from `and + verb`, sequence adverbs, `before/after + infinitive`.
* **Canonicalizations** (all tested): `at_least N + at_most M` = `range`; `unless X` = `if not X`; `only if` = necessary condition; litotes (`no dejes de X`) = `X`; `not … more than N` = `at most N`;
  negative quantifiers (`to no one`, `to anyone` under negation) = `any` under negation; `only V … when X` = `V … only when X`.

## Verdict (compare.py)
`NOT_EQUIVALENT` only when a **modelled** slot definitively differs or one side adds/loses content words that are not repetitions of what the other
side already says. `EQUIVALENT` needs every slot equal. Everything else is `INCONCLUSIVE`, with the reasons listed. Deliberate suppressions (they can only turn a
`NOT_EQUIVALENT` into `INCONCLUSIVE`, never create an `EQUIVALENT`): unrecognized or generic action on one side; an unrepresentable construct (fractions, else-branches);
ambiguous condition scope; an unresolved pronoun or light verb that may stand in for content; cross-language identical spellings (false friends).

## Reliable NOT_EQUIVALENT (added 2026-10-03)
Error analysis of blind14 found that 32 of 71 `NOT_EQUIVALENT` verdicts were wrong: paraphrases or undecidable pairs. Root cause: a slot that is present on one side and
absent on the other was always reported as a definitive difference, even when the other text carried words that could express the same idea in a construction the parser
does not model (`unless X` vs `provided … doesn't`; `no more than` vs `must not exceed`). Rule now enforced in `compare.py::_reliable_filter`:
* **presence mismatch** (A has the slot, B lacks it): definitive only if B says nothing that A does not already say;
* **value conflict** (both have the slot): definitive only if neither side has unexplained content words;
* **extra words** (items-level addition/loss): definitive only if *anchored* — a proper name, a number, a noun of the closed lexicon, or a prepositional phrase. A lone adjective,
  adverb or filler (`ainda`, `próprio`, `bancaria`) is INCONCLUSIVE ("may be a paraphrase marker");
* repeated words (said elsewhere in the same text, or already inside a condition/exception/quantity unit) are ellipsis, not additions;
* object pronouns and light verbs may stand in for content; possessives (`su`) may stand for `of X`.
Cost: recall. On dev data the system proves "different" for about half of the truly different pairs and says INCONCLUSIVE for the rest.

## Measured evidence so far (all on closed controlled-domain instructions, author-labelled, ES/EN/PT, 140 pairs per set)
| set | role | false-equivalent | NOT_EQUIVALENT precision | proven equivalent |
|---|---|---|---|---|
| blind13 | first independent run of the OLD rules route | 52.8% | n/a | 37.3% |
| blind14 | independent, 0.3-R model before the reliability filter | 0/85 | 39/71 = 55% | 0/55 |
| blind15 | independent, after the reliability filter | 0/77 | 28/35 = 80% (gate 90%: FAIL) | 1/63 |
| blind16 | independent, after closing blind15's classes | **2/82 = 2.4%** | 27/31 = 87.1% (gate 90%: FAIL) | 1/58 |
| blind17 (short, 70) | hybrid verification | semantic 2/42; **hybrid false-SAME 2/42 = 4.8% (gate 2%: FAIL)**, same as the arbiter alone | semantic 13/15 | arbiter 28/28, hybrid 27/28 |
| blind18 (short, 70, ambiguity-heavy) | ambiguity-veto test, 2 judges | semantic 3/44 = 6.8%; **hybrid false-SAME 2/44 vs arbiter alone 4/44** | semantic 10/14 | arbiter 24/26, hybrid 21/26 (80.8%, gate 85%: FAIL) |
Each fresh independent set has exposed new defect classes (about 10-20% of NOT_EQUIVALENT verdicts wrong); dev-set numbers (~98%) are not predictive because they are tuned on.
The semantic track is a loss/distortion DETECTOR in a closed domain, not a prover of equivalence; for proof of open-text paraphrase the 2-of-2 LLM arbiter remains the baseline (docs/EVIDENCE.md).

## Known limits (do not claim otherwise)
Closed lexicon (about 100 action stems, ~70 noun synonyms): any other word is an opaque item, so true paraphrases with different vocabulary are `INCONCLUSIVE`. Modifier-attachment ambiguity is only caught through repetition
heuristics. No syntax tree. Relative-time arithmetic (`mañana` vs `dentro de 24 h`) is not modelled. Cross-language equivalence works only for words in the synonym table.
Numbers: bare `10` vs `exactly 10` is left INCONCLUSIVE on purpose (implicit exactness). Evidence: golden_r and blind13 are DEVELOPMENT sets for this track; the independent number is blind14.


## Hybrid decision (`aixl.semantic.hybrid_decide`, option 3 of 2026-10-03)
The semantic track is a cheap **loss/distortion detector and veto**; only the 2-of-2 LLM arbiter (`aixl.arbiter`, docs/EVIDENCE.md) can **prove** sameness. The core calls no model.
| arbiter | semantic | verdict |
|---|---|---|
| DIFFERENT | any | DIFFERENT (a dissent always blocks sameness) |
| SAME | NOT_EQUIVALENT | **REVIEW** (conflict, a human decides) — never SAME |
| SAME | EQUIVALENT / INCONCLUSIVE | SAME |
| UNSURE | any | UNSURE (+ hint when the semantic model suspects a difference) |
| no judges | NOT_EQUIVALENT | DIFFERENT, `proven_by = semantic-suspect` (suspected: measured precision 80-87%) |
| no judges | else | UNSURE (the semantic track alone never proves sameness) |
`short_circuit=True` skips the judges when the semantic model says NOT_EQUIVALENT. Decisions are memoised by `aixl.arbiter.DecisionMemo`.

**blind17 verdict on the hybrid (2026-10-03):** the semantic veto did NOT add protection on this set (it fired once, falsely; the arbiter's two wrong SAMEs were not vetoed: one has a disputed label, one is a double negation the semantic model can only flag as INCONCLUSIVE).
Candidate rule, not implemented (needs data): arbiter SAME + semantic INCONCLUSIVE carrying an `AMBIGUOUS_*` flag -> REVIEW. Do not claim the hybrid is safer than the arbiter alone until a set shows the veto catching a wrong SAME.

**blind18 verdict (2026-10-03):** the ambiguity veto caught 2 arbiter false-SAMEs (benefit 2) and sent 3 true SAMEs to review (cost 3); R1 passed, R2 (80.8% < 85%) and R3 (1/2) failed, so the claim "the hybrid is safer than the arbiter alone" is still NOT allowed.
What the evidence supports: on ambiguity-heavy text the arbiter alone made 4 false-SAMEs in 44 (9.1%), and the hybrid turns a share of them into a REVIEW queue (~8% of pairs here) at the price of also reviewing some true SAMEs.
Use it where a wrong SAME is costlier than a human review (destructive / financial instructions); do not present REVIEW as an error: it means "needs a person".
