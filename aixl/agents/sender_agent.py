"""E-AUTONOMOUS (2026-09-30): a REAL, standalone MCP server playing the SENDER side of a negotiation
— a genuinely separate OS process from the receiver driver (aixl/autonomous_negotiation.py), talking
to it only over real MCP stdio JSON-RPC. Holds either an original natural-language instruction
(--text) or an already-encoded AIXL line (--aixl, for replaying a real historical encoding, e.g. a
genuine Sonnet/Gemini disagreement from E-INTEROP).

Computes its canonical form FRESH on every `answer()` call from that stored source — never a value
cached once at negotiation setup and replayed — directly closing the "is the ANSWER a live
confirmation from a running sender, or a value copied at simulation start?" gap the E-MCP
third-party test (Claude Desktop, 2026-09-30) raised about the single-process aixl/negotiation.py.

Run standalone: `python -m aixl.agents.sender_agent --text "Close ticket #77."`"""
import argparse

import aixl
from aixl.serialization import aixl_codec

_parser = argparse.ArgumentParser()
_group = _parser.add_mutually_exclusive_group(required=True)
_group.add_argument("--text", help="Original natural-language instruction this sender holds.")
_group.add_argument("--aixl", help="An already-encoded AIXL line this sender holds (replay mode).")
_args = _parser.parse_args()


def _canonical() -> dict:
    """Recomputed on every call by design — see module docstring."""
    if _args.text:
        return aixl.to_semantic(_args.text).canonical()
    return aixl_codec.decode(_args.aixl).canonical()


def _message_aixl() -> str:
    return aixl.to_aixl(_args.text) if _args.text else _args.aixl


from mcp.server.mcpserver import MCPServer  # noqa: E402 (after arg parsing, deliberately)

server = MCPServer(
    name="aixl-sender-agent", version=aixl.__version__,
    instructions="Sender side of an AIXL negotiation. get_message() returns this agent's own "
                 "AIXL-encoded message (the REQUEST payload); answer(dim) answers a CLARIFY question "
                 "about one canonical() dimension of it, recomputed fresh from the stored source "
                 "on every call.",
)


@server.tool(description="Return this sender's own AIXL-encoded message (the REQUEST payload).")
def get_message() -> dict:
    return {"aixl": _message_aixl()}


@server.tool(description="Answer a CLARIFY question about one canonical() dimension of this "
                          "sender's own message (e.g. 'actions', 'negation', 'time').")
def answer(dim: str) -> dict:
    v = _canonical().get(dim, "")
    return {"value": list(v) if isinstance(v, tuple) else v}


def main():
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
