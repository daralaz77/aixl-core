# E-MCP — a THIRD, independently-built MCP client: Antigravity CLI (Google), 2026-09-30

The path here was long, and worth recording honestly: Gemini Desktop's own UI does not expose
custom MCP server configuration (confirmed by hunting through every Settings section and the
compose-bar "Más herramientas" menu — it only has "Inteligencia personalizada"). `gemini-cli`
(the older, separate Google CLI, installed via `npm install -g @google/gemini-cli`) DOES have a
working `gemini mcp add` command and a clean `~/.gemini/settings.json`, but its personal "Sign in
with Google" OAuth flow is now DISCONTINUED server-side ("This client is no longer supported for
Gemini Code Assist for individuals... migrate to the Antigravity suite of products") — an external
deprecation, not something fixable from this project. Google's successor product, **Antigravity**
(a whole new agentic dev platform: IDE, CLI, SDK), does support the same personal Google OAuth login
and has its own `agy mcp` command.

## Installation and registration
```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash   # user ran this themselves (blocked for
                                                                # this session by the auto-mode
                                                                # classifier as a curl|bash pattern)
~/.local/bin/agy mcp add --env PYTHONPATH=$HOME/.claude/skills/aixl-core \
    aixl-core $HOME/.claude/skills/aixl-core/.venv/bin/python -- -m aixl.mcp_server
```
`agy mcp list` confirmed: `aixl-core  stdio  enabled  .../.venv/bin/python -m aixl.mcp_server`.

## Auth: two credentials the user entered themselves, never handled by this project
1. An API key pasted into chat by mistake (for the abandoned `gemini-cli` path) — never used, user
   was told to treat it as exposed and regenerate it if concerned.
2. A one-time OAuth authorization code pasted into chat by mistake (for `agy`'s browser login) — never
   used (it had already expired: the CLI's 60s wait had timed out before it was pasted). The user then
   completed the full OAuth browser flow and the first-run onboarding (theme picker, Terms of Service,
   workspace trust) themselves, directly in the terminal — this project never touched either credential.

## Client: Antigravity CLI (`agy`), interactive TUI, user-driven
User typed, in an ordinary `agy` chat session:
> Usa la herramienta aixl_compare para comparar "Elimina el reporte." con "No elimines el reporte." y
> muéstrame el resultado JSON completo.

Antigravity's own agent (model: Gemini 3.8 Flash) recognized and called the real tool
(`aixl-core/aixl_compare`), asked for the user's explicit tool-call approval (a real permission gate,
answered "1. Yes, allow tool call" by the user), and returned:
```json
{
  "equivalent": false, "similarity": 0.7, "drift": 0.3, "drift_level": "CRITICAL_DRIFT",
  "differences": [{"field": "NEGATION", "source": "NOT_SPECIFIED", "target": "FORBID:DELETE",
                   "kind": "added", "severity": "CRITICAL", "detail": "prohibition/permission changed"}],
  "per_dimension": {"intent": 1.0, "actions": 1.0, "entities": 1.0, "negation": 0.0},
  "explanation": "NEGATION: NOT_SPECIFIED -> FORBID:DELETE (CRITICAL)"
}
```
Matches this project's own reproduction of the same call exactly (see `results_mcp_desktop_client_FIRST_RUN.md`).

## Status: THREE independent vendors' MCP clients now confirmed
Anthropic (Claude Desktop, all 3 tools), OpenAI (ChatGPT/Codex, `aixl_compare`), Google (Antigravity
CLI, `aixl_compare`). Still n=1 for `aixl_compare` on this client; `aixl_translate`/`aixl_negotiate`
not yet tried via Antigravity.

## Update: aixl_negotiate confirmed too (same session, same day)
User asked, in the same `agy` chat session: "Usa la herramienta aixl_negotiate para negociar entre
el emisor 'Close ticket #77.' y el receptor 'Delete ticket #77.'...". Antigravity's agent called
`aixl-core/aixl_negotiate` (again behind a real tool-approval gate) and returned:
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
Matches this project's own reproduction of the identical call exactly (see `results_mcp_desktop_negotiate_FIRST_RUN.md`). `aixl_negotiate` is now confirmed on all 3 independent vendor clients (Claude Desktop, and now Antigravity CLI; not yet on Codex).

## Update: aixl_translate confirmed too (same session, same day)
User asked: "Usa la herramienta aixl_translate para traducir 'Analiza las ventas del primer
trimestre de 2026.'...". Antigravity's agent called `aixl-core/aixl_translate` and returned:
```json
{
  "aixl": "V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES T:Q1-2026",
  "semantic": {"intent": "REQUEST_ANALYSIS", "actions": ["ANALYZE"], "entities": [], "data": ["SALES"],
               "time": ["Q1-2026"], "location": [], "constraints": [], "conditions": [], "negation": [],
               "references": [], "quantities": [], "goal": "", "output": [], "modifiers": []},
  "ambiguous": false
}
```
Matches this project's own reproduction exactly (see `results_mcp_desktop_translate_FIRST_RUN.md`).

## Status: ALL 3 tools now confirmed on Antigravity CLI
`aixl_compare`, `aixl_negotiate`, `aixl_translate` — all three, in the same `agy` session, all matching
this project's own reproductions exactly. Antigravity CLI (Google) now has the same tool coverage as
Claude Desktop (Anthropic); only Codex (OpenAI) still has just `aixl_compare` tested.
