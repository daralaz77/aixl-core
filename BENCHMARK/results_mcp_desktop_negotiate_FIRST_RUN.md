# E-MCP — aixl_negotiate tested from Claude Desktop (2026-09-30)

## Client: Claude Desktop main chat (independent process, user-driven)
User called `aixl_negotiate(sender_text="Close ticket #77.", receiver_text="Delete ticket #77.")`
from an ordinary Claude Desktop chat conversation. Reported transcript (paraphrased by the user,
values verbatim): REQUEST -> CLARIFY (ACTION: receiver read DELETE, sender's own message implies
UPDATE) -> ANSWER (UPDATE) -> ACCEPT. Zero remaining differences.

## Reproduction from this Code session (frozen, machine-readable)
```json
{
  "converged": true,
  "rounds": 1,
  "transcript": [
    "NEGOTIATE X=REQUEST MSG=M1",
    "NEGOTIATE X=CLARIFY MSG=M2 REF=M1 DIM=actions CANDIDATES=DELETE;UPDATE Q=\"ACTION: receiver read 'DELETE', sender's own message implies 'UPDATE' — which is correct?\"",
    "NEGOTIATE X=ANSWER MSG=M3 REF=M2 DIM=actions VALUE=UPDATE",
    "NEGOTIATE X=ACCEPT MSG=M4 REF=M3"
  ],
  "remaining_differences": []
}
```
Matches the Desktop client's report exactly. Closes "no third party has called aixl_negotiate".

## Real design limitation found by the SAME Desktop client's own critical reading (verified, not just asserted)
The Desktop-side Claude instance noted, correctly: the ANSWER turn's value isn't a fresh
confirmation from a live sender — it's read straight back out of the sender's OWN already-computed
canonical form (`sender_canonical.get(dim, "")`, `aixl/negotiation.py:181`), derived once at the very
start of `negotiate()` from the same original sender text that produced the disagreement in the
first place. When the sender's phrasing is unambiguous (as in "Close ticket #77." above) this is
harmless: re-deriving from the same text just re-confirms the same correct value. But when the
sender's phrasing does NOT resolve to a clear action, the mechanism still reports a confident ACCEPT.

**Confirmed with a constructed case** (`aixl_negotiate("Quita el ticket #77.", "Elimina el ticket #77.")`):
"quita" is not in the rule-based translator's vocabulary at all, so the sender's own re-derived value
for the `actions` dimension is `NOT_SPECIFIED` (empty). The receiver's confident, plausibly CORRECT
reading (`DELETE`, from "elimina") gets silently overwritten with `NOT_SPECIFIED` and the exchange
still reports **ACCEPT / converged**, with `remaining_differences: []`:
```json
{
  "converged": true,
  "rounds": 1,
  "transcript": [
    "NEGOTIATE X=REQUEST MSG=M1",
    "NEGOTIATE X=CLARIFY MSG=M2 REF=M1 DIM=actions CANDIDATES=DELETE;NOT_SPECIFIED Q=\"ACTION: receiver read 'DELETE', sender's own message implies 'NOT_SPECIFIED' — which is correct?\"",
    "NEGOTIATE X=ANSWER MSG=M3 REF=M2 DIM=actions VALUE=NOT_SPECIFIED",
    "NEGOTIATE X=ACCEPT MSG=M4 REF=M3"
  ],
  "remaining_differences": []
}
```
This is worse than an honest REJECT: a downstream system reading this transcript sees "CONVERGED,
0 remaining differences" and has no signal that the resolution actually threw away the only concrete
information either side had. Not fixed yet — flagged to the user as a design decision (change
`negotiate()` to REJECT, or leave a note, when the sender's own re-derived value for the disputed
dimension is itself NOT_SPECIFIED/empty) rather than silently patched, since it changes negotiate()'s
semantics for every caller.
