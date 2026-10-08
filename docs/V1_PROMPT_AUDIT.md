# Audit: "AIXL Interoperability Translator v1.0" prompt vs aixl-core (2026-10-08)

Method: each section of the prompt was run against the real code; status is what was observed, not what docs claim.
Tests: `tests/test_gate_v1.py` (8) — full suite 1070 passed.

| § | Requirement | Status | Evidence |
|---|---|---|---|
| 1, 23 | Use AIXL only if tokens(AIXL) < tokens(original), else MODE=NATURAL | **WAS ABSENT → closed** (`aixl/gate.py`) | before: wire `V:AIXL-0.3 I:REQUEST_TRANSLATION ...` was longer than the input |
| 2, 6 | Minimal form (`TRN DOC EN`), omit empty fields | **PARTIAL → closed** | compact L1 drops V:/I:/G: (decoder re-derives them, fingerprint-verified) and abbreviates 4 tags |
| 5, 13 | Decode and verify before emitting | closed | gate requires fingerprint(decode(expand(compact))) == fingerprint(source) |
| 12 | Negations/numbers never lost | covered | "No elimines los datos originales" keeps N:NO_DELETE / K:FORBID_DELETE |
| 14 | Don't over-encode | closed | "Hola" produced EMPTY AIXL before; now NATURAL (`no_action`) |
| 16 | Fidelity > compression | **DEFECT found → closed** | "...conserva solamente la información más importante" was silently dropped; gate now blocks via `check_completeness` |
| 17 | ES/EN/PT → same representation | covered | identical fingerprint for the 3 translate examples |
| 8, 18 | Handshake / negotiation | covered (previous work) | `aixl_negotiate`, `aixl_negotiate_autonomous` (2 real processes) |
| 19 | Partial fallback | covered in spirit | UNRECOGNIZED_TERMS / completeness; per-fragment `FALLBACK:` text not emitted |
| 5 (SIM≥0.98) | Self-computed similarity gate | **REPLACED on purpose** | fingerprint + completeness instead; self-judged SIM was disproved by blind10 (99.4% → 24–43%) |
| 7, 9, 10, 11-L2, 20, 21 | Auto-detect, UNK/DEF, adaptive dictionary, L2, self-optimization, vocab evolution | **not probed today** | design-only / unmeasured; §10 and §21 are Option 3 (measure) |

## Measured effect of the gate (228 own-author dev texts + 3 long realistic prompts)
- AIXL used: **5 / 228** (2%); NATURAL: 223. Reasons: no_token_saving 194, incomplete_encoding 25, no_action 4.
- Mean saving when AIXL is used: 16.4%.
- The 3 long prompts: 0 used AIXL (2 incomplete, 1 AIXL longer than the text).

**Honest conclusion:** with AIXL 0.3 wire syntax, token compression of single human instructions is rarely real.
The value of the stack is verified *equivalence/loss detection*, not compression. Token counts use a deterministic
proxy (no tokenizer installed; real tokenizers will differ) and the corpus is own-author, so this is a dev-set signal, not blind evidence.

## Option 3 — §10 adaptive dictionary and §21 vocabulary evolution (2026-10-08)
Script: `benchmarks/v1_dict_atoms_eval.py` (+ a 5-seed held-out split run inline). Own-author dev corpus, proxy tokenizer.

**§10 session dictionary** (definition cost paid, replaced only when GAIN>0; sessions built to share a target = BEST case):
- on compact AIXL messages: saving 11.7% (3 msgs), 18.4% (5), 27.0% (10); 20-msg sessions: no pool large enough, not measured.
- on natural text: 5.2% but n=1 session → inconclusive.
- Reading: real but only for long sessions that repeat the same tags; nothing for one-off messages. Not wired into the gate.

**§21 evolved atoms** (abbreviate the 12 most frequent unabbreviated tags, e.g. A:ANALYZE→A:ANA):
- in-sample: AIXL used 3 → 10 of ~190 texts, mean saving 11% → 18%, 0 fingerprint failures.
- held-out (derive on half, evaluate on other half, 5 seeds): AIXL used ≈2.0 → ≈4.8 of ~114 texts (≈2% → ≈4%), 0 fingerprint failures in all 5.
- Reading: gain is real but small; the learned abbreviations are corpus-specific (sales/customers), and truncations like `T:Q1-` are ugly.
  NOT merged into `ABBR`: promoting them needs a corpus from real traffic, not this dev set.

**Verdict:** both mechanisms help marginally and are safe (the fingerprint gate caught nothing because nothing broke), but neither changes the main conclusion: single human instructions rarely compress with AIXL; the stack's measured value is equivalence/loss detection.

## Real messages + real BPE tokenizer (2026-10-08)
Script: `benchmarks/v1_real_eval.py`. Corpus: 1449 unique real user messages from the owner's local Claude Code transcripts
(read locally, never sent anywhere). Tokenizer: tiktoken o200k_base (real BPE, **not Claude's tokenizer**).
- Gate result: AIXL 6 / 1449 (0.4%); NATURAL 1443. Reasons: incomplete_encoding 1347, no_token_saving 50, no_action 42, fingerprint_mismatch 4.
- By length (tokens): ≤15 → 980 msgs, 6 AIXL; 16–60 → 351, 0; 61–250 → 36, 0; >250 → 82, 0.
- **The 6 "wins" are not real wins.** They are 1-verb outputs from conversational filler: "creo que ya revisa" → `A:CHECK`,
  "si muestrame" → `A:GET`, "ya me logee por favor correlo tu" → `A:EXECUTE`. The saving comes from dropping context ("creo que", "ya me logee")
  that `check_completeness` does not flag. **Open defect:** the completeness check is too permissive for very short messages.
- Domain mismatch: real messages are conversational, mostly replies/bug reports, not the structured instructions AIXL targets.

### Fix for the short-message hole + re-measurement (2026-10-08)
Cause: `check_completeness` exempts the FIRST content word as "the verb", so in "creo que ya revisa" the verb was `creo` and the real verb `revisa`
carried the action while "creo que" vanished; and any lexicon-known word counted as accounted even when absent from the graph ("redacta el correo" → `A:GENERATE`, object lost).
Fix (`gate.strict_complete`): the exempt verb is the span the action regex really matched; no action span → NATURAL; every other content word must be in the graph
(or be a surface form of an entity/data class that IS in the graph, or a unit/month/language/number atom). Tests: 1072 pass (+2 regression tests).
- Real messages (1452, o200k_base): AIXL **6 → 1** (0.07%). The 5 removed were all lossy. The remaining one, `si muestrame` → `A:GET` (5 → 3 tokens), drops the affirmation "si" ("yes, show me").
  Residual weakness: affirmation/discourse markers are in the function-word list, so they are not treated as content.
- Dev set (228 texts): AIXL uses unchanged (3 base, 10 with evolved atoms) → the fix removed false wins without hurting the structured cases.

### Affirmations as content (2026-10-08)
`si muestrame` ("yes, show me") → `A:GET` dropped the affirmation because it sits in the function-word list. `gate.AFFIRM` (si/yes/ok/vale/claro/dale/listo/sim/...)
now blocks AIXL when such a word is present and not carried by the graph. Real messages (1468): **AIXL 0 / 1468**; dev set unchanged (3 / 10 with evolved atoms); 1073 tests pass.
Caveat: the list is closed and small (ES/EN/PT); an affirmation outside it would still be dropped. Ambiguous `si` (yes vs if) is treated conservatively as content.

## Option A validated: telegraphic form (2026-10-08)
Code: `aixl/telegraph.py` (closed vocabulary from the ontology, NOT from the test corpus; unknown word → `TelegraphError`, fail closed),
`benchmarks/v1_telegraph_eval.py`, `tests/test_telegraph.py` (suite 1081 pass). Example: `Analiza las ventas del primer trimestre de 2026` → `analyze sales q1-2026`.
Pipeline per text: graph → compact → telegraph → (decode telegraph → graph) must have the SAME fingerprint, then `check_completeness` + `strict_complete`, then tokens(tele) < tokens(natural) (o200k_base).

| Corpus | n | usable (AIXL-telegraph) | mean saving when used | fingerprint mismatches |
|---|---|---|---|---|
| dev set (own-author) | 225 | **128 (57%)** | **40.8%** | 0 |
| real user traffic | 1629 | **4 (0.25%)** | 48.8% | 0 |

- First run showed 35 mismatches: all were MY decoder bugs (abbreviations `cmp/trn/doc` not expanded, `@acme` case). The fingerprint check caught them; fixed, then 0.
- 4 dev codec failures (`this_week`, `last_week`) = vocabulary gap, closed by adding relative-time words.
- Real traffic: 1220 incomplete (the ontology doesn't cover conversational messages), 402 codec failures (free-text residue `F:` can't be expressed), 4 usable:
  `borra el modelo de Ollama`→`delete model @ollama`, `revisa`/`verifica`→`check`, `verifica tu`→`check` (drops "tu"; weak, function word).
- **Verdict:** Option A is a real syntax win (≈41% fewer tokens, lossless by fingerprint) for the structured instructions the ontology covers, but it does not change the
  real-traffic picture: 95.6% of tokens sit in long pasted messages and 98% of messages fall outside the ontology. Fidelity is only relative to the translator's graph.

## Option C: content references instead of resending (2026-10-08)
Code: `aixl/refstore.py` (RefStore: runs of ≥200 chars of lines already sent in the SAME conversation become `⟦=msg:first-last⟧`; every encode is verified by decode()==original, else sent raw),
`tests/test_refstore.py` (3), `benchmarks/v1_refstore_eval.py`. Corpus: all text blocks (user, assistant text, tool results) of 409 real local Claude Code sessions, 43.7M chars.
- Where the volume is: **tool results 79.0%**, user text 13.1%, assistant text 8.0%.
- Saved by within-session pointers: **17.3% of all chars** (tool results 19.9%, user text 11.6%, assistant text 1.7%). 7,899 blocks encoded, 0 round-trip failures (guarded).
- Exact o200k tokens on a sample of the ENCODED blocks only: 913,898 → 481,097 (−47.4%). This is per encoded block, not overall; the overall saving is the 17.3% char figure.
- Biggest sessions: 16–38% saved.
- Not measured / caveats: (1) a pointer is only useful if the model reads it correctly — answer quality with pointers is UNTESTED; (2) in real API use previous turns are often prompt-cached, so the billing effect
  is smaller than the token effect; (3) cross-session dedupe needs a shared store (not built); (4) 681 .jsonl files, 409 contributed blocks (others empty/sub-agent logs).
- Verdict: unlike A (tiny share of traffic), C addresses the part of the traffic that is actually big (tool output) and works on every message regardless of language/ontology.

### Option C quality test: can a model use pointers? (2026-10-08)
Scripts: `benchmarks/v1_refquality_build.py` (12 real tool-output pairs, seed 11, secrets filtered; 2 questions each = 24: "exact text of line N of MESSAGE 1", where line N lies INSIDE the span a pointer replaces; truth computed, not judged),
`benchmarks/v1_refquality_grade.py`. Model: Sonnet (one subagent per condition, Read tool only, told not to run code). Mean message: 2028 chars full vs 956 chars with pointers (−53% on these pairs).

| Condition | Exact-line accuracy |
|---|---|
| full text | 23/24 |
| pointers + 1-line legend | 22/24 |
| pointers, no legend | 24/24 |

- Differences are within noise (n=24, one model, one run). No evidence of degradation; no evidence of improvement either.
- Failures: full text missed 1 (case 1, line 3); legend missed case 4 lines 46 and 52 (answered a different nearby line — line-counting across a pointer is the observable risk).
- A grading bug of mine (truth lines carried a `N<tab>` prefix) initially showed 12/24 for everything; fixed by normalizing both sides before comparing.
- Not tested: reasoning tasks over pointed content (summaries, edits), models other than Sonnet, long chains of pointers (pointer → message that itself holds pointers), weaker models. Only lookups by exact line were measured.
