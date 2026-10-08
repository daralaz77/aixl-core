"""E-AUTONOMOUS (2026-09-30): drive a REAL negotiation between two SEPARATE, independently-running
OS processes over the real MCP transport — no human relays a single turn between them.

Everything up to this point (aixl/negotiation.py's `negotiate()`, and the E-MCP third-party client
tests) exercised the negotiation protocol with either both canonical forms already known to a single
caller, or a human copying a prompt from one chat window into another. This module is the missing
piece: the sender is a genuinely separate process (aixl/agents/sender_agent.py, spawned as its own
OS subprocess); this module plays the receiver, asking it real questions over stdio JSON-RPC via the
official `mcp` SDK client and getting back live answers.

Deliberately reuses `_negotiate_core` from aixl/negotiation.py — the exact same round-loop `negotiate()`
itself runs (audit finding #4, closed 2026-09-30: the two used to be independent ~40-line copies of the
same control flow; now there is exactly one). The only thing this module supplies is WHERE the sender's
canonical form and per-dimension answers come from: a live remote process over real MCP stdio JSON-RPC,
instead of a local dict already held in memory. See tests/test_autonomous_negotiation.py for parity
tests proving the two agree."""
import asyncio
import json

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from aixl.core.ontology import load_config
from aixl.negotiation import NegotiationOutcome, _negotiate_core
from aixl.serialization import aixl_codec


def _coerce(receiver_value_before, wire_value):
    """The sender agent sends JSON (tuples become lists); restore the receiver's own value's type
    so `belief[dim]` stays consistent with what compare_canonical/_fmt/_is_empty expect elsewhere."""
    if isinstance(receiver_value_before, tuple):
        if isinstance(wire_value, list):
            return tuple(wire_value)
        return (wire_value,) if wire_value else ()
    return wire_value


def _sender_env_and_cwd() -> tuple[dict, str]:
    """The nested sender-agent subprocess must NOT rely on the `mcp` SDK's default environment
    inheritance (mcp.client.stdio.DEFAULT_INHERITED_ENV_VARS = HOME/LOGNAME/PATH/SHELL/TERM/USER —
    notably NOT PYTHONPATH): when this negotiate_autonomous_async runs inside an MCP server that was
    ITSELF launched by a host app (Claude Desktop/Codex/Antigravity) with a minimal, replaced `env`
    (typically just {"PYTHONPATH": ...}), the outer process's own os.environ may already be missing
    PATH/HOME/etc, so the SDK's "safe" default for the nested child ends up even thinner. Always pass
    an explicit env (PYTHONPATH + whatever PATH/HOME/etc this process actually has) and an explicit
    cwd, rather than depending on implicit inheritance across two layers of MCP process spawning."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LOGNAME", "SHELL", "TERM", "USER")}
    env["PYTHONPATH"] = root
    return env, root


async def negotiate_autonomous_async(sender_command: list[str], receiver_canonical: dict,
                                      config: dict | None = None, max_rounds: int = 3,
                                      msg_prefix: str = "M") -> NegotiationOutcome:
    """Async core, exported so a caller already running inside an event loop (e.g. an MCP server's
    own tool handler — see aixl/mcp_server.py's aixl_negotiate_autonomous) can `await` it directly
    instead of going through the sync `negotiate_autonomous()` wrapper, which cannot be called from
    a running loop (asyncio.run() would raise).

    Spawns the real sender-agent subprocess and, once the session is live, delegates the entire
    REQUEST -> CLARIFY -> ANSWER -> ACCEPT/REJECT round-loop to `_negotiate_core` (aixl/negotiation.py)
    — the two `get_request`/`get_answer` closures below are the only thing specific to talking to a
    real remote process instead of reading a local dict."""
    cfg = config or load_config()
    sender_env, sender_cwd = _sender_env_and_cwd()
    params = StdioServerParameters(command=sender_command[0], args=sender_command[1:],
                                    env=sender_env, cwd=sender_cwd)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def get_request():
                msg = await session.call_tool("get_message", {})
                sender_aixl = json.loads(msg.content[0].text)["aixl"]
                return aixl_codec.decode(sender_aixl).canonical(), sender_aixl

            async def get_answer(dim, belief):
                ans = await session.call_tool("answer", {"dim": dim})
                wire_value = json.loads(ans.content[0].text)["value"]
                return _coerce(belief.get(dim), wire_value)

            return await _negotiate_core(receiver_canonical, cfg, max_rounds, msg_prefix, get_request, get_answer)


def negotiate_autonomous(sender_command: list[str], receiver_canonical: dict, config: dict | None = None,
                          max_rounds: int = 3, msg_prefix: str = "M") -> NegotiationOutcome:
    """Spawn `sender_command` (a real `python -m aixl.agents.sender_agent ...` invocation) as a
    genuinely separate OS process and drive a full REQUEST -> CLARIFY -> ANSWER -> ACCEPT/REJECT
    exchange with it over real MCP stdio JSON-RPC. No human relays any turn. Mirrors
    `aixl.negotiation.negotiate`'s signature and return type (NegotiationOutcome)."""
    return asyncio.run(negotiate_autonomous_async(sender_command, receiver_canonical, config, max_rounds, msg_prefix))
