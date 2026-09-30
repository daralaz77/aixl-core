# E-NEGOTIATE live demo transcript (2026-09-29)

Real instruction: "Update today's inventory report." Two independent AIXL encodings genuinely disagreed
(this is real E-INTEROP round-3 data, t013/S9-010): Sonnet wrote `D:REPORT`, Gemini wrote `D:REPORT,DATA`.

Two SEPARATE Sonnet subagents played the two roles, each given ONLY `data/negotiation/protocol_spec.md`
(no code access, no access to each other's reasoning) and the turn(s) addressed to them so far.

**v1 spec (had a bug):** `CANDIDATES=<a>,<b>` with no other convention. The receiver agent naturally wrote
`CANDIDATES=REPORT,DATA,REPORT` for its multi-value candidate — indistinguishable, once parsed, from three
separate one-word candidates. Caught immediately by running the REAL `negotiation.decode()` on the agent's
own real output (not by unit tests, which had all used single-word candidates and missed it).
Fixed: `;` separates candidates, `,` stays free inside one candidate (`aixl/negotiation.py`, `test_bug` /
`test_candidates_use_semicolon_...`, `data/negotiation/protocol_spec.md` updated with an explicit example).

**v2 spec, real transcript (all 3 lines are the literal, unedited output of two separate model calls):**
```
NEGOTIATE X=REQUEST MSG=M1 PAYLOAD="V:AIXL-0.3 I:REQUEST_EXECUTION A:UPDATE D:REPORT T:TODAY"
NEGOTIATE X=CLARIFY MSG=M2 REF=M1 DIM=data CANDIDATES=REPORT,DATA;REPORT Q="DATA: receiver read REPORT,DATA, sender's payload only has REPORT — does the update also cover the underlying data, or just the report itself?"
NEGOTIATE X=ANSWER MSG=M3 REF=M2 DIM=data VALUE=REPORT
```
The sender agent re-read the ORIGINAL text ("Update today's inventory report.") and correctly answered
`REPORT` — the same value Sonnet had independently encoded in the first place, and the semantically
correct one (the instruction never mentions "the data" as a separate target). All 3 lines decode cleanly
with the real `aixl.negotiation.decode()` (verified, not assumed).

This is a small, bounded demonstration (one dimension, one round, one real disagreement) that an
independent model can correctly SPEAK a brand-new wire format from documentation alone — a stronger check
than unit tests written by the same session that built the protocol, but still a demo, not a claim that
the mechanism has been stress-tested at scale with live models. The deterministic convergence measurement
(21/21 real E-INTEROP disagreements, `benchmarks/negotiation_eval.py`) is the "EVIDENCE"-tier result; this
transcript is closer to "REAL VALIDATION" tier but limited to one case.
