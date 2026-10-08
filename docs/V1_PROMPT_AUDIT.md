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
