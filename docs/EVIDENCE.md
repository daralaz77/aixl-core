# Evidence and recommended use (state 2026-11-26, release 0.8.1; blind sets up to blind34)

Sections 1-4 and 4e are current. Sections 2 and 3 hold the October measurements; the later ones (rule comparator, hybrid, judges; blind19-34) are in [§4e](#4e-rule-comparator-hybrid-and-judges-blind19-34-2026-11-03--2026-11-18). **Read §4e before quoting any false-"same" rate**: blind11/12 are not the worst case.

This page is the single source of truth for **what has been measured about AIXL and what it supports**. Every number links to a result file or to
[adr/ADR-017.md](adr/ADR-017.md) (full tables, setup, limits). If another document disagrees with this page, this page wins; superseded text is archived in
[HISTORY.md](HISTORY.md). Status labels follow master prompt §36: HYPOTHESIS · DESIGN · IMPLEMENTATION · EXPERIMENT · RESULT · LIMITATION.

## 1. What to use for what

| You need | Use | Why (RESULT) |
|---|---|---|
| Decide whether two **open-text** instructions (ES/EN/PT) mean the same | **Full-text arbiter, 2-of-2**: two independent LLMs read both original texts under strict rules (`aixl/resources/arbiter_rules_v1.txt`, texts treated as data); "same" only if both say SAME; **store the verdict** (decision memo). Implemented as the audit layer `aixl.arbiter` (0.5.0, [ADR-018](adr/ADR-018.md)) | 359–360/360 equivalent pairs recovered and **0/480 false "same" on one-detail near-misses** (blind12); 100 % / 0.6 % false on blind11; 1 error in 70 attacks written to fool it. **Later sets chosen to be subtle are worse: false "same" from 0 % up to 11.7 %** (§4e) |
| Reduce wrong "same" before an irreversible action | **Hybrid** `aixl_hybrid_decide(..., strict=True)`: the two judges AND a rule-based proof; otherwise `REVIEW` ([HYBRID_MCP.md](HYBRID_MCP.md)) | In-vocabulary pairs (blind29/30): false "same" 1/60 and 0/60 against 7/60 and 6/60 for the judges alone, accepting about half of the equivalents. Outside the comparator's vocabulary it sends almost everything to review (blind26/27: 0 equivalents proven) |
| Exact, offline, free equivalence **inside a controlled vocabulary** | AIXL rules route (`aixl.compare`) | 99.4 % on the project's own 5×100 benchmark (same author as the code), 0.85 ms/pair. On other authors' open text this route is *not* safe (next row). The separate rule comparator `compare_texts` has its own measurements in §4e |
| Detect that something was lost, never say "equal" without proof | AIXL with `inconclusive` on (opt-in; completeness + structural markers + `R:` residue) | False "equivalent" 47–59 % → 0–2 % on blind10/blind11, **but proves 0–17 % of true equivalents**: it is a loss detector, not a prover |
| Input hygiene against invisible characters / look-alike letters | `sanitize_input` (always applied by the translator) | 0 false rejections on 71 benign pairs; caught the Cyrillic-homoglyph class that a single cheap judge missed (post-hoc, one set) |
| Cheap candidate generation before an arbiter | A plain lexical overlap filter (**not** AIXL's key) | blind12: lexical Jaccard ≥ 0.1 keeps 60.3 % of equivalent pairs at 1.3 % of all pairs; AIXL canonical/fingerprint key keeps 15.8 % at 0.28 % |
| An interchange format with an audit trail | AIXL line + MCP/A2A adapters + stored decisions | Real clients from three vendors called the MCP server (engineering evidence, not accuracy); the format itself is not shown to improve meaning preservation |

**Do not** claim: that AIXL proves equivalence of free-text paraphrases; that the 99.4 % / 95 % figures are general accuracy; that AIXL is better than
sending both texts to a strict LLM judge (no measurement shows it adds correctness to that baseline); that it is a standard or universal.

## 2. The measurements, in order

All "blind" sets were written by a model **without access to the repository**; each is evaluated once and is then *spent* (no tuning on it afterwards).

| # | Set (authors) | What was run | Headline RESULT | Detail |
|---|---|---|---|---|
| 1 | Own 5×100 benchmark (same author as code) | rules route | 497/500 = 99.4 % | BENCHMARK.md. **Not independent**: inherits the translator's vocabulary |
| 2 | blind10 — 150 + 150 cases (Opus, Haiku) | rules route; LLM route (card 0.3) | **24.7–40.0 %** and **37.0 %**; ~60 % of non-equivalent pairs judged EQUIVALENT because the format has no slot for the rest of the meaning and drops it silently | LIMITATIONS.md E-BLIND10 |
| 3 | blind10 | AIXL-side repairs: `inconclusive`, `R:` residue, per-side completeness, typed keys | false "equivalent" → 0–2 %; proven equivalents only 2–17 % (typed keys 10 %, gate + residue judge 32 %) | ADR-016, ADR-017 |
| 4 | blind10 | full-text arbiter (Sonnet, Haiku, 2-of-2) | 56–60/60 proven, 0/180 false | ADR-017 |
| 5 | blind10 adversarial + red-team (Opus, told the arbiter's rules) | arbiter vs attacks (injection aimed at the judge, hidden negation, scope, locale, homoglyphs, role swap, conditionals, polarity, partial commit) | consensus fooled by 1/70; injection 0/8; single Haiku fooled by 4/70 | ADR-017 |
| 6 | blind10 subset, 82 pairs × 5 passes × 2 models | repeatability | verdict flips: Sonnet 1.2 %, Haiku 6.1 %, 2-of-2 1.2 %; errors are systematic, not noise | ADR-017 |
| 7 | **blind11** — 300 cases (Sonnet), run once | every arm (rules 0.4, rules+inconclusive, AIXL LLM route on two encoders, arbiter alone / 2-of-2 / + sanitizer / + AIXL gate) | rules 0.4: 50 % proven but **40.6 % false**; AIXL LLM route: 0 % proven; **arbiter 2-of-2: 100 % proven, 0.6 % false** | `data/blind10/blind11_result.txt` |
| 8 | **blind12** — 360 texts, 60 clusters, 2 new authors, run once | stage-1 candidate keys + stage-2 arbiter on 840 pairs | AIXL key recall 15.8 % (gate ≥ 80 % **failed**); lexical baseline 60.3 %; arbiter 2-of-2: 359/360 equivalent, **0/480** near-miss false "same" | `data/blind10/b12_stage1_result.txt`, `b12_stage2_result.txt` |

Pre-registered gates were written before blind11 and blind12 outputs existed (ADR-017 "PRE-REGISTRATION" sections). The arbiter passes them; the AIXL
semantic layers do not.

## 3. Cost and latency (estimates; no live API call was made)

Per 1 000 pairs, proxy tokenizer ±20 %, prices from the claude-api skill table cached 2026-09-25 (check before budgeting), thinking tokens not counted:

| Path | Latency | Cost |
|---|---|---|
| AIXL deterministic compare | 0.85 ms/pair (0.85 s per 1 000) | $0, offline |
| Arbiter Sonnet 5.5 | ≈ 3.5 min sequential (one call if parallel) | ≈ $0.16 |
| Arbiter Haiku 4.5 | ≈ 14.7 min sequential | ≈ $0.12 |
| **Arbiter 2-of-2** | max of the two in parallel | **≈ $0.28** (≈ $0.14 with Batch API) |
| AIXL LLM-route encoders (card 0.6) | 47–176 s per 90 texts | ≈ $1.13 Sonnet (≈ 7× the arbiter) and 0 % proven on blind11 |

The arbiter is paid **per pair** (all pairs over N texts = N(N−1)/2: N = 10 000 → ≈ $8–14 k); encoding is paid **per text** (N = 10 000 ≈ $6). A cheap
lexical stage 1 reduces arbiter calls ~77× at 60 % recall (blind12). Decision memos make each pair a one-time cost.

## 4. What is NOT shown (LIMITATION)

* Whether AIXL adds *correctness* over the arbiter baseline in any setting; its remaining candidate value is deterministic/offline exact proofs in controlled vocabularies, cacheable fingerprints for exact duplicates, a machine-checkable format and audit trail — none measured against the baseline except cost.
* Recall of any cheaper stage-1 design built after seeing blind12 (embedding-based blocking was not tested); false "same" on the 63 780 cross-cluster pairs in blind12 that were not judged.
* Only ES/EN/PT; mostly instruction-like texts (blind27 is encyclopedic); labels are almost all model-written (blind27 is the one human-labelled set, 100 pairs; blind34 has 954 pairs but very noisy labels); arbiter prompts were fixed in advance but other wordings may shift recall/precision; no repeatability beyond 5 passes; arbiter latency measured through agents (includes harness overhead).
* Judges from other families were tried (§4e) and showed no combination clearly better than two Claude judges; the open models ran quantised, with one prompt, on a few sets. Other commercial vendors' judges were not tested.
* AMBIGUOUS class: the rules route detects 16.7 % of ambiguous free-text instructions and flags 11.7 % of non-ambiguous ones (blind11); no arbiter arm was run for it.
* Nothing here is validated with real agent-to-agent traffic or any real organisation.
* The sanitizer-veto result (Haiku alone 4 → 1 false "same" on blind10-adversarial) was chosen after seeing the data and was neither confirmed nor refuted by blind11/12 (no obfuscation attacks in them).

## 4b. The 0.3-R semantic track (closed controlled domain, 2026-10-03) — what was measured and what it supports
Code `aixl/semantic/` (model, parser, comparator, hybrid), documented in [SEMANTIC_MODEL_0_3R.md](SEMANTIC_MODEL_0_3R.md). Scope: imperative / rule-style instructions in ES, EN, PT with a closed lexicon; everything else is `INCONCLUSIVE`. All sets below are author-labelled by fresh agents with no access to the repo; each independent set was evaluated once on hash-frozen code and is then spent (data/blind13-18, pre-registrations in each PREREG.md).
| What | Result (independent sets) | Supports |
|---|---|---|
| Old rules route on open text (blind13) | 52.8% false-equivalent | confirms 0.5.0 findings |
| Semantic track false-equivalent (blind14-18, 5 sets) | 0/85, 0/77, 2/82, 2/42, 3/44 | a **loss/distortion detector** that is usually, not always, safe; never claim "0 errors" |
| `NOT_EQUIVALENT` precision (gate 90%) | 55% -> 80% -> 87% -> 87% -> 71% across sets | **NOT_EQUIVALENT is a suspicion, not a proof**; two attempts failed the 90% gate |
| Proven equivalent (gate 70%) | 0-2% | the semantic track cannot prove sameness of paraphrases (closed lexicon) |
| Hybrid (arbiter proves, semantic vetoes) on ambiguity-heavy text (blind18) | false-SAME 2/44 vs arbiter alone 4/44; SAME on equivalent 80.8% (gate 85%: fail); 1 of 2 ambiguity-REVIEWs right (gate 60%: fail) | a **review queue** for high-stakes cases; the claim "safer than the arbiter alone" is NOT allowed by the pre-registered policy |
Development sets (golden_r + blind13-18 after fixes, 766 pairs): NOT_EQUIVALENT precision 184/190, false-equivalent 2/464 — tuned on, so not evidence. Every fresh independent set exposed new defect classes (10-20% of NOT_EQUIVALENT verdicts), so the closed lexicon has a long tail.
**Use:** where a wrong SAME costs more than a human review (destructive / financial instructions), run `aixl.semantic.hybrid_decide` with two judges and treat REVIEW as "a person decides". **Do not use it** to certify that two open-text instructions are equivalent, nor to present NOT_EQUIVALENT as proven.

## 5. Reproduce

```bash
cd ~/.claude/skills/aixl-core
.venv/bin/python -m pytest -q                                               # unit/regression/doc tests
.venv/bin/python -m benchmarks.sil5x100_eval                                # own benchmark (not independent)
.venv/bin/python -m benchmarks.blind10_eval data/blind10/haiku.jsonl        # rules route on another author's set
.venv/bin/python -m benchmarks.blind11_eval data/blind10                    # blind11, every arm (set is spent)
.venv/bin/python -m benchmarks.funnel_eval stage1                           # blind12 stage 1 (deterministic)
.venv/bin/python -m benchmarks.funnel_eval stage2 data/blind10              # blind12 stage 2
.venv/bin/python -m benchmarks.repeatability_eval data/blind10              # arbiter repeatability
```
Frozen sets carry their sha256 (`data/blind10/blind11.sha256`, `blind12.sha256`); verify with `shasum -a 256 -c`. LLM outputs are stored next to each set so every table can be recomputed without new model calls.


## 4d. AIXL 0.4 atom layer (2026-10-04) — see docs/ATOMS.md, docs/ATOMS_EVIDENCE.md, ADR-019
Two LLMs annotating the same unseen natural instruction agree on the whole atom graph ~35 % of the time (F1 ≈ 0.83) under guides v0.2/v0.3/v0.4 (32.7/35.3/36.0 %, noise ±4); the rule extractor reaches F1 0.27–0.37 on unseen sets and declares 0/450 complete (no silent errors); dev numbers (93–98 %) are tuning artefacts. A cross-model round trip through AIXL (3 models, 40 cases, both directions) keeps F1 0.93 / core 0.97, equal to the two-independent-readers floor. Atoms = verifiable interchange + measuring instrument, not a free-text meaning extractor.
LLM wrapper with abstention (ADR-020): two independent calls per text, accept only on agreement. blind3: `core` accepts 67 % at core F1 0.93 (0.67 abstained). Replication on blind4 (pre-registered, new author): 54 % at 0.92 (0.72 abstained) — quality separation replicated, but the declared ≥55 % coverage floor failed by one point, so the claim is downgraded to "coverage 54–67 %". Pooled 300: `core` 60 % at 0.92 vs 0.70; `exact` 34 % at exact-graph 0.65 vs 0.19.

## 4e. Rule comparator, hybrid and judges: blind19-34 (2026-11-03 → 2026-11-18)

Continues §4b: "comparator" means `aixl.semantic.compare_texts`. "False accept" = it said `EQUIVALENT` on a pair not labelled equivalent (`UNDECIDABLE` counts as not equivalent). Each set was pre-registered and evaluated once, then spent. Unless noted, authors and judges are Claude models and labels are the authors'.

### Comparator, new construction families (`data/blind19` … `blind25`, 80 pairs each)
| Set | False accepts (gate ≤ 3 %) | `NOT_EQUIVALENT` precision (gate 90 %) | Equivalents proven |
|---|---|---|---|
| blind19 | 0/48 | 13/21 | 5/32 |
| blind20 | 4/49 | 11/19 | 4/31 |
| blind21 | 4/50 | 6/11 | 0/30 |
| blind22 | 0/47 | 7/12 | 0/33 |
| blind23 | 3/47 | 4/7 | 2/33 |
| blind24 | 2/53 | 4/9 | 0/27 |
| blind25 | 3/48 | 3/5 | 3/32 |
| **sum** | **16/342 (4.7 %)** | **48/84 (57 %)** | **14/218 (6.4 %)** |

Neither claim ("does not fail silently on new families", "NOT_EQUIVALENT is reliable") was ever allowed on both gates; the code changed between sets, so the sum describes a sequence of versions, not one.

### Comparator inside its own constructs, and paired recall attempts
| Set | What | Result | Pre-registered rule |
|---|---|---|---|
| blind28 (120) | in-vocabulary, 3 judges | proved 24/60 equivalents, **4/60 false accepts, all also accepted by both Claude judges** | safety gate fails |
| blind29 (120) | old vs new comparator | false accepts 2 → 1 of 60; 31/60 equivalents proven (net +2) | recall (+5) fails |
| blind30 (120) | universal-quantifier and passive rules | 0 false accepts of 60; proven 28 → 30 of 60 | recall (+5) fails; passive rule reverted |
| blind31 (120) | 'by' passive rule | 0/63 false accepts; target construct 5 → 6 of 20 | recall (+5) fails; **not merged** |
| blind32 (60) | one lexicon entry (bounds) | no new false accept; 16 → 17 of 30 | recall (+2) fails; **not merged** |
| blind33 (270, three fresh authors) | 0.7.1 / patch 0005 / 0.8.0 | false accepts 11 → 8 → **0** of 135; equivalents proven 3 → 2 → **1** of 135 | safety and binding hold; recall fails. 61 of 128 unproven equivalents differ in words with no known synonym |
| blind34 (954, open-model authors) | same three trees | false accepts 42 → 40 → 29 of 474 **by author labels, which are very noisy** (a judge majority contradicts 138 of 954); proven 10/480 in all three | safety and no-regress hold |

blind34 post-hoc (not blind): pairs accepted by the comparator that both Claude judges call `DIFFERENT`: 17 (0.7.1), 6 (0.8.0), 1 after the 0.8.1 modal guard (`data/blind34/POSTHOC.md`). Two edits made after the blind33 run are likewise checked only on spent sets (`data/blind33/POSTRUN.md`). Independent adversarial audits behind the 0.8.0 safety fixes are summarised in `CHANGELOG.md`; most of their numbers are development evidence.

**Supports:** a loss detector that fails closed on much unfamiliar wording. **Does not support:** "never accepts a wrong pair", or proving open-domain equivalence (about 0-6 % of equivalents proven on unfamiliar wording; 40-52 % only inside the constructs it was tuned on).

### Judges and hybrid
False "same" on pairs not labelled equivalent / equivalents accepted:

| Sets | Two judges, no veto | Default hybrid (`veto="all"`) | Strict (comparator must prove) |
|---|---|---|---|
| blind19-25 | 24/342 (7.0 %) / 196 of 218 | 19/342 (5.6 %) / 175 of 218 | 0/342 / 11 of 218 (comparator tuned on these sets) |
| blind26 | 3/53 (5.7 %) / 25 of 27 | 3/53 / 19 of 27 | 0/53 / 0 of 27 (vacuous) |
| blind27 (human labels) | 1/50 (2.0 %) / 28 of 50 | 1/50 / 24 of 50 | vacuous (0 of 50 proven) |
| blind28 | 6/60 (10 %) | not reported | no protection: comparator's 4 false accepts passed the judges too |
| blind29 | 7/60 (11.7 %) / 60 of 60 | not reported | 1/60 / 31 of 60 |
| blind30 | 6/60 (10 %) / 60 of 60 | not reported | 0/60 / 30 of 60 |
| blind31 | 6/63 (9.5 %) / 57 of 57 | not reported | 0/63 / 26 of 57 |
| blind33 (spent when judged) | 0/135 / 134 of 135 | 0/135 / 117 of 135 | not measured here |

* **`veto="definite"`** (opt-in, 0.8.0): equivalents accepted 117 → 129 of 135 (blind33) and 110 → 112 of 120 (360 adversarial pairs); false "same" unchanged (0/135; 3/240) (`data/blind33/hybrid/RESULT_veto.md`). In those 630 pairs the veto caught no judge error. **It is not shown to be free elsewhere:** on blind19-25 `veto="all"` removed 5 false "same" (24 → 19), and on blind34 `veto="definite"` accepted 390 of 480 equivalents against 358, with false "same" 125 against 101 **by the noisy author labels** (both Claude judges said SAME on those pairs, so the data cannot tell whether the stricter veto stopped real errors).
* **Short-circuit:** a definite comparator `NOT_EQUIVALENT` had 95 % precision on 810 spent pairs; skipping the judges there gives "different, suspected", not proof.
* **Two judges, not one:** Haiku alone said SAME on 18 % of 240 adversarial non-equivalents, 2-of-2 on 1.3 %. The two Claude judges err together far more than chance, so a third judge of the same family is not an independent check.
* **Other families:** Qwen2.5-7B (local, blind28) said SAME to 35 of 60 non-equivalents. On Colab (`data/blind33/colab/`) a single open judge was weaker than the Claude pair (false "same" 29 % at 7B, 10 % at 32B, 5 % for a strict 24B) and a third family mostly cost equivalents. On blind34 Gemma-3-27B agreed with the Claude pair on 793 of 954 pairs.

### What to take from §4e
1. The 0/480 of blind12 is one favourable condition; on subtle families expect several percent of false "same" from two judges.
2. Before an irreversible action use `strict=True` or a person; expect many `REVIEW`s.
3. Growing the comparator's closed lists has not met a pre-registered recall rule in blind29-33.
4. The next informative measurement needs human labels and real agent traffic; neither exists yet.
