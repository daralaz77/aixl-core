# E-MCP — aixl_translate tested from Claude Desktop (2026-09-30)

## Client: Claude Desktop main chat (independent process, user-driven)
User called `aixl_translate("Analiza las ventas del primer trimestre de 2026.")` from an ordinary
Claude Desktop chat conversation. Reported output matches this project's own reproduction exactly
(below), including `ambiguous: false`.

## Reproduction from this Code session (frozen, machine-readable)
```json
{
  "aixl": "V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES T:Q1-2026",
  "semantic": {
    "intent": "REQUEST_ANALYSIS", "actions": ["ANALYZE"], "entities": [], "data": ["SALES"],
    "time": ["Q1-2026"], "location": [], "constraints": [], "conditions": [], "negation": [],
    "references": [], "quantities": [], "goal": "", "output": [], "modifiers": []
  },
  "ambiguous": false
}
```

## Third-party model's own critical reading (worth keeping, not a bug)
The Desktop-side Claude noted that `ambiguous: false` means the sentence PARSES cleanly, not that it
is COMPLETE for unsupervised execution: no entity/region/product/channel, no `goal`, no `output`
format, and Q1 is assumed calendar-year without flagging that a different fiscal year would change it.
This is accurate and matches `ambiguity.py`'s documented design: it only flags known blocking patterns
(PRONOUN_NO_ANTECEDENT, VAGUE_TIME, MISSING_YEAR, etc.), not "is this instruction fully specified for
autonomous execution" — a broader, harder, not-yet-attempted question. No code change proposed by this
finding; recorded as a genuine, useful observation about how to READ the tool's output, not a defect.

## Status: all 3 exposed tools now confirmed with a real third-party MCP client
`aixl_compare` (results_mcp_desktop_client_FIRST_RUN.md), `aixl_negotiate`
(results_mcp_desktop_negotiate_FIRST_RUN.md — which also led to a real bug fix), and now
`aixl_translate`. Still n=1 per tool (one call each, one Desktop session) — no other client, and no
production-scale usage, has touched this server yet.
