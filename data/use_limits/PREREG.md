# Preregistration — USE_LIMIT family (boundary markers) on FRESH model-written relays (2026-10-29), evaluated ONCE

Why: a probe of 12 hand-written pairs (same author as the code: indicative only, now SPENT) showed that `relay_check` missed 7 of 12 relays that dropped a PURE use-limit marker
(`Confidential.`, `Embargoed.`, `under NDA`, `For management eyes.`) because those markers carry no negation, `only`, number, date or modal. `ok: true` then reads as "no critical slot
changed" although a confidentiality notice vanished. The literature motivation is a 2026 preprint on "boundary metadata collapse" (facts survive hand-offs, use-limit markers do not).
Improvement under test: a new family `USE_LIMIT` (closed-class markers, ES/EN/PT, language-independent codes), added to RELAY_FAMILIES. It was designed from the 12 spent pairs and from
general knowledge of the marker kinds, NOT from the data below.

Authors: two models (Opus -> out_A, Sonnet -> out_B), told to act as an intermediate agent, NOT given the repository, the code, the previous data or the family. Each writes its OWN 40 fresh
instructions (ES / EN / PT, about 13 each) and, per instruction, one JSON line with: `source` (an instruction that CONTAINS one use-limit marker of the given style), `faithful_light`
(near-verbatim relay, marker kept), `faithful_heavy` (strongly reworded relay, marker kept but re-expressed in different words), `limit_drop` (relay that loses ONLY the marker) and `control`
(relay with ONE non-marker corruption: negation, number, date_time or condition). Marker styles (balanced): `confidentiality` (confidential, internal, privileged, classified),
`legal_status` (under NDA, embargoed, under legal review, subject to contract), `audience` (for management / the finance team / the board — written WITHOUT the word only/solo/apenas),
`doc_status` (draft, preliminary, unverified, provisional). The marker must not contain a negation, a number, a date or a modal verb.
The outputs are written before anyone (including the evaluator) reads them; only line counts are reported back.

Frozen code: FREEZE.json (sha256 of aixl/invariants.py and its dependencies; RELAY_FAMILIES old and new). Nothing is tuned after reading; a failing hypothesis is reported, not repaired.
Baseline = the SAME data scored with the OLD families (RELAY_FAMILIES without USE_LIMIT).
Hypotheses (decided now):
 U1  limit_drop relays flagged by the NEW `relay_check` >= 70 %   (and each of the four styles >= 50 %; a style below is a finding)
 U2  faithful_light relays flagged by the NEW `relay_check` <= 10 % (do no harm)
 U3  control corruptions flagged >= 70 %  (sanity: the detector still works)
 U4  false alarms CAUSED BY the new family alone (flag by USE_LIMIT and by no other family) on faithful_light <= 3 % and on faithful_heavy <= 10 %
Reported regardless: baseline flagged on limit_drop (expected well below U1), faithful_heavy flagged overall (expected high: not a gate), the missed limit_drops, which families fired on faithful_light.
