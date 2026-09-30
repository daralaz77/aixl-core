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
