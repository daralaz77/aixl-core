"""A REAL MCP server exposing AIXL 0.3 over the actual protocol (official `mcp` SDK, stdio transport).

Run it directly: `python -m aixl.mcp_server`. Any real MCP client (Claude Desktop, `mcp` SDK client, any other
agent) can then call these tools over stdin/stdout using the genuine JSON-RPC 2.0 MCP wire format — this is
the piece that used to be `NotImplementedError` in aixl/adapters/protocol_adapter.py (E-MCP, 2026-09-30).

Exposes: aixl_translate, aixl_compare, aixl_negotiate — thin wrappers around the existing, already-tested
aixl.api.service functions. No new semantics are introduced here; this module is transport only."""
from mcp.server.mcpserver import MCPServer

import aixl

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


def main():
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
