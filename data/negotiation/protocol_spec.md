# AIXL Negotiation Protocol (E-NEGOTIATE, 2026-09-29) — spec for an agent

When two agents' AIXL encodings of the same instruction disagree, instead of silently guessing, use this
exchange. It is a SEPARATE wire format from AIXL itself (it CARRIES an AIXL line as payload where relevant,
but is not parsed by the AIXL codec). One line per turn, always starting with the literal word `NEGOTIATE`,
followed by `KEY=VALUE` tokens separated by spaces. A value with a space or comma must be double-quoted.

Tokens: `X=<type>` (REQUEST | CLARIFY | ANSWER | ACCEPT | REJECT) · `MSG=<id>` (a short id you invent for
this turn, e.g. M1, M2, M3...) · `REF=<id>` (the id of the turn you are replying to) · `DIM=<dimension>`
(the ONE canonical dimension in dispute: intent, actions, entities, data, time, location, constraints,
conditions, negation, references, quantities, goal, output, or modifiers — always the plain lowercase word)
· `CANDIDATES=<a>;<b>` (the two competing readings, separated by `;` — NOT `,`, because one reading can
itself be a comma-joined list when the disputed dimension holds several values, e.g. `REPORT,DATA;REPORT`
means candidate 1 is "REPORT,DATA" and candidate 2 is "REPORT") · `Q="<question>"` (why you are asking) ·
`VALUE=<v>` (the resolved value, for an ANSWER) · `REASON="<...>"` (for a REJECT) · `PAYLOAD="<AIXL line>"`
(for a REQUEST).

Turn types:
- `X=REQUEST`: a normal instruction, PAYLOAD carries the AIXL line.
- `X=CLARIFY`: sent by the RECEIVER when its own reading of a message disagrees with what it received on
  ONE dimension. Name that ONE dimension in DIM=, both readings in CANDIDATES=, and a short Q= explaining
  the disagreement. Ask about the MOST CONSEQUENTIAL disagreement if there is more than one (a negation or
  destructive-action mismatch matters more than a wording/order mismatch).
- `X=ANSWER`: sent by the SENDER (who holds the original instruction and is authoritative) in reply to a
  CLARIFY. VALUE= carries the correct value for that ONE dimension, decided from the ORIGINAL instruction
  text, never invented.
- `X=ACCEPT` / `X=REJECT`: end the exchange (not asked of you in this task).

Example exchange:
```
NEGOTIATE X=REQUEST MSG=M1 PAYLOAD="V:AIXL-0.3 I:REQUEST_EXECUTION A:DELETE Y:#77"
NEGOTIATE X=CLARIFY MSG=M2 REF=M1 DIM=actions CANDIDATES=DELETE;UPDATE Q="ACTION: receiver read DELETE, but 'close a ticket' is usually a status change — which is correct?"
NEGOTIATE X=ANSWER MSG=M3 REF=M2 DIM=actions VALUE=UPDATE
```
A multi-value dimension (data/entities/etc. can hold several values at once) still uses ONE candidate per
whole reading: if you read `D:REPORT,DATA` and the sender's payload says `D:REPORT`, that is
`CANDIDATES=REPORT,DATA;REPORT` — two candidates (`REPORT,DATA` and `REPORT`), not four.
