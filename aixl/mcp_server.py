"""A REAL MCP server exposing AIXL 0.3 over the actual protocol (official `mcp` SDK, stdio transport).

Run it directly: `python -m aixl.mcp_server`. Any real MCP client (Claude Desktop, `mcp` SDK client, any other
agent) can then call these tools over stdin/stdout using the genuine JSON-RPC 2.0 MCP wire format — this is
the piece that used to be `NotImplementedError` in aixl/adapters/protocol_adapter.py (E-MCP, 2026-09-30).

Exposes: aixl_translate, aixl_compare, aixl_negotiate — thin wrappers around the existing, already-tested
aixl.api.service functions. Also aixl_negotiate_autonomous (E-AUTONOMOUS, 2026-09-30): calling it makes
THIS server spawn a genuinely separate sender-agent OS process and negotiate with it over real MCP
stdio, with zero human relay — so a real third-party MCP client can trigger the autonomous 2-process
exchange itself, not just a script. No new semantics are introduced here; this module is transport only."""
from mcp.server.mcpserver import MCPServer

import aixl
from aixl.autonomous_negotiation import negotiate_autonomous_async

server = MCPServer(name="aixl-core", version=aixl.__version__,
                    instructions="Translate ES/EN/PT instructions to AIXL 0.3 and compare/negotiate them "
                                 "for semantic equivalence, drift, ambiguity and contradiction.")


@server.tool(description="Translate a natural-language instruction (ES/EN/PT) into AIXL 0.3 and its canonical form.")
def aixl_translate(text: str) -> dict:
    r = aixl.translate(text)
    return {"aixl": r["aixl"], "semantic": r["semantic"], "ambiguous": r["ambiguity"]["ambiguous"]}


@server.tool(description="Compare two instructions (or AIXL messages) for semantic equivalence, similarity, drift.")
def aixl_compare(a: str, b: str) -> dict:
    return aixl.compare(a, b).to_dict()


@server.tool(description="Resolve a disagreement between a sender and a receiver instruction via a bounded, "
                          "severity-ordered clarification exchange. Returns ACCEPT (converged) or REJECT.")
def aixl_negotiate(sender_text: str, receiver_text: str, max_rounds: int = 3) -> dict:
    out = aixl.negotiate(sender_text, receiver_text, max_rounds=max_rounds)
    return {"converged": out.converged, "rounds": out.rounds,
            "transcript": [t.encode() for t in out.transcript],
            "remaining_differences": [d.to_dict() for d in out.remaining_differences]}


@server.tool(description="Resolve a disagreement via an AUTONOMOUS negotiation between two genuinely "
                          "separate OS processes with zero human relay: this server spawns a real "
                          "sender-agent subprocess holding sender_text and negotiates with it over "
                          "real MCP stdio JSON-RPC. Returns ACCEPT (converged) or REJECT.")
async def aixl_negotiate_autonomous(sender_text: str, receiver_text: str, max_rounds: int = 3) -> dict:
    import sys, traceback
    receiver_canonical = aixl.to_semantic(receiver_text).canonical()
    sender_cmd = [sys.executable, "-m", "aixl.agents.sender_agent", "--text", sender_text]
    try:
        out = await negotiate_autonomous_async(sender_cmd, receiver_canonical, max_rounds=max_rounds)
    except Exception as e:                                        # noqa: BLE001 — surface it, don't swallow it
        return {"error": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc(),
                "sender_command": sender_cmd}
    return {"converged": out.converged, "rounds": out.rounds,
            "transcript": [t.encode() for t in out.transcript],
            "remaining_differences": [d.to_dict() for d in out.remaining_differences]}


def main():
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
