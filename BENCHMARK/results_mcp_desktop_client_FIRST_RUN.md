# E-MCP — real third-party MCP client validation (2026-09-30)

Server: `aixl/mcp_server.py` (stdio transport), registered in
`~/Library/Application Support/Claude/claude_desktop_config.json` under `mcpServers.aixl-core`,
pointing at `.venv/bin/python -m aixl.mcp_server` with `cwd`/`PYTHONPATH` set to the repo root.

## Client 1: Claude Desktop main chat (independent process, user-driven)
User called `aixl_compare("Elimina el reporte.", "No elimines el reporte.")` from an ordinary
Claude Desktop chat conversation (NOT this Code session, NOT the test suite). Reported output
(pasted verbatim by the user):

> Equivalentes: No · Similitud: 0.70 · Deriva: 0.30 (CRITICAL_DRIFT)
> Única diferencia: NEGATION, NOT_SPECIFIED -> FORBID:DELETE, severity CRITICAL.

## Client 2: this Claude Code session (separate process, same call, for a frozen record)
Called directly via `mcp__aixl-core__aixl_compare` right after the user's report, to freeze an
exact machine-readable result:

```json
{
  "equivalent": false,
  "similarity": 0.7,
  "drift": 0.3,
  "drift_level": "CRITICAL_DRIFT",
  "differences": [
    {"field": "NEGATION", "source": "NOT_SPECIFIED", "target": "FORBID:DELETE",
     "kind": "added", "severity": "CRITICAL", "detail": "prohibition/permission changed"}
  ],
  "critical_changes": [
    {"field": "NEGATION", "source": "NOT_SPECIFIED", "target": "FORBID:DELETE",
     "kind": "added", "severity": "CRITICAL", "detail": "prohibition/permission changed"}
  ],
  "per_dimension": {"intent": 1.0, "actions": 1.0, "entities": 1.0, "negation": 0.0},
  "explanation": "NEGATION: NOT_SPECIFIED -> FORBID:DELETE (CRITICAL)"
}
```

## Conclusion
Two independently-driven MCP clients (Claude Desktop's own chat interface, and this separate Code
session), talking to the SAME real running server over the SAME stdio config, both got the correct,
identical result. This closes the honest gap noted after E-MCP's first build: until now the only
client that had ever talked to `aixl_server.py` was this project's own pytest subprocess. n=1 case
(one comparison, one server session) — breadth (more tools, more disagreement cases, a real
negotiation round-trip through this transport) is still future work, not claimed here.
