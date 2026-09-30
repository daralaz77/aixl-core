# E-MCP — SECOND, independently-built MCP client: ChatGPT/Codex (OpenAI), 2026-09-30

Until this point the only client that had ever talked to `aixl_server.py` was Claude Desktop
(Anthropic). This is a genuinely different vendor's client: OpenAI's ChatGPT desktop app (Codex),
registered via its own config format (`~/.codex/config.toml`, `[mcp_servers.aixl-core]`), a completely
separate codebase from Claude Desktop's `claude_desktop_config.json`.

## Registration
```toml
[mcp_servers.aixl-core]
command = "/Users/darwingperez/.claude/skills/aixl-core/.venv/bin/python"
args = ["-m", "aixl.mcp_server"]
cwd = "/Users/darwingperez/.claude/skills/aixl-core"

[mcp_servers.aixl-core.env]
PYTHONPATH = "/Users/darwingperez/.claude/skills/aixl-core"
```
Config backed up first (`config.toml.bak.20260929232812`); the exact entry was dry-run-verified with
the official `mcp` SDK's own client before asking the user to restart ChatGPT/Codex.

## Client: ChatGPT (Codex) main chat (independent process, user-driven)
User called `aixl_compare("Elimina el reporte.", "No elimines el reporte.")` from an ordinary
ChatGPT/Codex conversation. Reported: NOT equivalent, similarity 0.7, CRITICAL drift (0.3).

## Reproduction from this Code session (frozen, machine-readable)
```json
{
  "equivalent": false, "similarity": 0.7, "drift": 0.3, "drift_level": "CRITICAL_DRIFT",
  "differences": [{"field": "NEGATION", "source": "NOT_SPECIFIED", "target": "FORBID:DELETE",
                   "kind": "added", "severity": "CRITICAL", "detail": "prohibition/permission changed"}]
}
```
Matches exactly. Two independent vendors' MCP clients (Anthropic's Claude Desktop, OpenAI's
ChatGPT/Codex) have now both connected to this same real server over stdio and gotten the correct
result — a substantially stronger interoperability claim than a single vendor's client.

## Honest scope
n=1 for this client (one tool, one comparison). `aixl_translate`/`aixl_negotiate` not yet tried from
Codex. No other vendor's client (Gemini, a third framework) tried yet. No production-scale usage.

## Update: aixl_negotiate and aixl_translate confirmed too (same day)
User ran, in the same ChatGPT/Codex conversation:

`aixl_negotiate("Close ticket #77.", "Delete ticket #77.")`:
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

`aixl_translate("Analiza las ventas del primer trimestre de 2026.")`:
```json
{
  "aixl": "V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES T:Q1-2026",
  "semantic": {"intent": "REQUEST_ANALYSIS", "actions": ["ANALYZE"], "entities": [], "data": ["SALES"],
               "time": ["Q1-2026"], "location": [], "constraints": [], "conditions": [], "negation": [],
               "references": [], "quantities": [], "goal": "", "output": [], "modifiers": []},
  "ambiguous": false
}
```
Both match this project's own reproductions exactly (`results_mcp_desktop_negotiate_FIRST_RUN.md`,
`results_mcp_desktop_translate_FIRST_RUN.md`).

## Status: ALL 3 tools now confirmed on ALL 3 independent vendor clients
Claude Desktop (Anthropic), Antigravity CLI (Google), and now ChatGPT/Codex (OpenAI) all have
`aixl_compare`, `aixl_negotiate` and `aixl_translate` confirmed working correctly through real,
independently-built MCP clients this project never authored. Still n=1 per tool per client (one
call each); no production-scale/repeated usage yet.
