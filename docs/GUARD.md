# Internal guard (2026-10-07) — `aixl/guard`, profiles in `data/guard/`

**What it is.** A fail-closed check "did the candidate text keep the meaning of its source?" for three real surfaces:
ReclamaYa (user's requested remedy vs the AI-polished petition), CineMatch (backend validator message EN vs the Spanish text shown),
Robot School (mission instruction vs recorded actions). `PASS` = no known loss signal; everything else = `REVIEW`. PASS is not a proof.

**Layers (per profile JSON):** hidden/look-alike characters (`sanitize_input`) → canonical form (closed grammars) → numbers (digits + spelled) →
proper nouns → critical-term classes (negation, totality, cost, state, channel, remedy, direction, place, time…) → source-content coverage →
added-content cap → AIXL comparator (`aixl_mode`: required / advisory / off). Robot School's real input (Spanish instruction vs English
verb|description lists) is a *realization* check, not equivalence: `guard_actions` + `data/guard/robot_school_actions.json`.

**Measured (author-written sets, author-assigned labels; `data/guard/sets/`, frozen decisions; blind1-4 are spent).**
| | distorted pairs | guard false-PASS | **AIXL comparator alone** false-PASS | faithful auto-PASS (guard) |
|---|---|---|---|---|
| ReclamaYa petition | 67 | 0 | **29** | 43/48 |
| Robot School description | 64 | 0 | **32** | 30/49 |
| CineMatch EN→ES | 52 | 0 | 0 (but passes only 1/30 faithful) | 53/56 |
First contact with each *fresh* set (before any fix informed by it), ReclamaYa / Robot School / CineMatch false-PASS: blind1 3/16, 1/16, 1/13 · blind2 1/16, 1/16, 0/13 ·
blind3 4/18, 3/16, 0/13 · blind4 0/17, 0/16, 0/13. Real bugs found this way: `sin` + letter never matched as negation (regression test), `agua`→`energía`
(3-letter words ignored), `each value in` prefix not accepted for all fields. 0/46 on blind4 ⇒ 95 % upper bound ≈ 6 % (rule of three), not "0 %".

**Ablation (important):** with the rules layer present, the AIXL comparator added **0 unique catches** on blind1-4 and cost 3/24 faithful PASSes on ReclamaYa;
therefore `aixl_mode` is `advisory` for ReclamaYa/Robot School (verdict returned, not blocking) and `advisory` for CineMatch (AIXL cannot read EN validator
phrasing against ES). The AIXL comparator alone is **not** a guard on open text (45-50 % false-PASS here, consistent with EVIDENCE.md).

**Robot School real data:** 10 scored real production fixtures (`robot-school/services/api/scripts/fixtures`): rutina-02 ("señala" recorded as `display`, the documented DEC-005
mismatch) and the CORS artefact → REVIEW; 8 aligned episodes → PASS. **Rules were tuned while looking at these** — regression lock, not blind accuracy. Synthetic cross-pairing
(instruction i × actions j, mismatched by construction): 4/182 PASS, all 4 are legitimate overlaps (a recorded `drop into` does realise "suelta").

**Ports.** `lib/ai/guard/guard.ts` (ReclamaYa) and `packages/api-client/src/guard/guard.ts` (CineMatch) are the rules layer (= Python with `use_aixl=False`); parity tests assert identical
decisions on every frozen pair. `robot-school/services/api/src/instructionGuard.js` ports `guard_actions`. Profiles are the shared source of truth: edit `data/guard/*.json`, copy, re-run the parity tests.

**Limits.** Same author wrote lexicon and sets; single-word lexical classes will keep missing new vocabulary (each fresh set so far found some); Spanish only; ≤ 30 pairs per profile per set;
REVIEW rate on faithful paraphrase is 5-40 % depending on profile (cost = fallback/human, not wrong output). CLI: `cli.py guard {reclamaya|robot_school|cinematch} A B` (exit 3 on REVIEW).
