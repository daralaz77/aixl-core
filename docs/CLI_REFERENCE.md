# CLI reference

Run from the repo root: `python cli.py <command> …` (use the project venv: `.venv/bin/python cli.py …`). Add `--json` to a command that supports it for machine output.
The prompt's conceptual `aixl encode|decode|compare|validate|drift` map to the commands below (`encode`, `decode`, `validate` and `fingerprint` were added 2026-10-02).

| Command | Args | Does | Exit |
|---|---|---|---|
| `encode` | `"text"` | prints only the AIXL line | 0 |
| `translate` | `"text"` | AIXL line + canonical form + ambiguity flag (`--json`: full dict) | 0 |
| `decode` | `"AIXL line"` | prints the canonical form of an AIXL line (alias of `aixl`) | 0; raises on invalid |
| `validate` | `"AIXL line"` | `VALID` or `INVALID <code>: <detail>` | 0 valid · **1 invalid** |
| `fingerprint` | `"text"` | 16-hex semantic fingerprint (relative times use today's date) | 0 |
| `compare` | `"a" "b"` | equivalence, similarity, drift level, differences (`--json`) | 0 |
| `diff` | `"a" "b"` | human `SEMANTIC DIFF` | 0 |
| `drift` | `"a" "b"` | drift level + `CRITICAL_SEMANTIC_DRIFT` flag + differences (`--json`) | 0 |
| `ambiguity` | `"text"` | ambiguity result as JSON | 0 |
| `contradiction` | `"a" "b"` | contradiction result as JSON | 0 |
| `negotiate` | `"sender" "receiver" [--rounds N] [--json]` | bounded clarification exchange on two texts | 0 |
| `negotiate-aixl` | `"line" "line" [--rounds N] [--json]` | same, on two AIXL lines | 0 |
| `lab` | `"a" "b"` | rich CLI view of a comparison | 0 |
| `demo` | – | six demos with expected vs actual | 0 |
| `bench` | – | the 200-case dev benchmark summary (DEMO material) | 0 |
| `serve` | `[port]` | Semantic Lab web app (default 8765) | runs until stopped |
| `mcp-serve` | – | MCP server over stdio (needs `[mcp]` extra) | runs until stopped |

Examples
```bash
python cli.py encode "Envía el informe a Ana en PDF"
python cli.py validate "V:AIXL-0.3 A:SEND E:REPORT"     # VALID
python cli.py compare "Send the report." "Do not send the report."
python cli.py drift "Do not send the report externally." "Send the report externally."
```
Benchmarks are modules, not subcommands: `python -m benchmarks.sil5x100_eval`, `python -m benchmarks.sil_security_eval`, `python -m benchmarks.blind_eval --round N`.
