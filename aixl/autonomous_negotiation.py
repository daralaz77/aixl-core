"""E-AUTONOMOUS (2026-09-30): drive a REAL negotiation between two SEPARATE, independently-running
OS processes over the real MCP transport — no human relays a single turn between them.

Everything up to this point (aixl/negotiation.py's `negotiate()`, and the E-MCP third-party client
tests) exercised the negotiation protocol with either both canonical forms already known to a single
caller, or a human copying a prompt from one chat window into another. This module is the missing
piece: the sender is a genuinely separate process (aixl/agents/sender_agent.py, spawned as its own
OS subprocess); this module plays the receiver, asking it real questions over stdio JSON-RPC via the
official `mcp` SDK client and getting back live answers.

Deliberately reuses the exact turn semantics, severity ordering, wire format (NegotiationTurn) and
the actions-emptiness REJECT rule from aixl/negotiation.py (imported, never reimplemented) — the only
thing that changes is WHERE the sender's answer comes from: a live remote process instead of a local
dict read. `negotiate()` itself is untouched (its 141 existing tests keep passing unmodified); this
is pure addition. See tests/test_autonomous_negotiation.py for parity tests proving the two agree."""
import asyncio
import json

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from aixl.core.comparator import compare_canonical
from aixl.core.ontology import load_config
from aixl.serialization import aixl_codec
from aixl.negotiation import (
    NegotiationTurn, NegotiationOutcome, worst_dimension, _dim_of_label, _is_empty, _fmt,
)


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
    a running loop (asyncio.run() would raise)."""
    cfg = config or load_config()
    belief = dict(receiver_canonical)
    transcript: list[NegotiationTurn] = []
    n = 0
    mid = 0

    def next_id():
        nonlocal mid
        mid += 1
        return f"{msg_prefix}{mid}"

    sender_env, sender_cwd = _sender_env_and_cwd()
    params = StdioServerParameters(command=sender_command[0], args=sender_command[1:],
                                    env=sender_env, cwd=sender_cwd)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            msg = await session.call_tool("get_message", {})
            sender_aixl = json.loads(msg.content[0].text)["aixl"]
            sender_canonical = aixl_codec.decode(sender_aixl).canonical()

            req_id = next_id()
            transcript.append(NegotiationTurn("REQUEST", req_id, payload=sender_aixl))
            last_id = req_id

            while n < max_rounds:
                result = compare_canonical(sender_canonical, belief, cfg)
                if result.equivalent:
                    acc_id = next_id()
                    transcript.append(NegotiationTurn("ACCEPT", acc_id, ref_id=last_id))
                    return NegotiationOutcome(True, n, transcript, belief, [])
                d = worst_dimension(result)
                dim = _dim_of_label(d.field)
                n += 1
                clarify_id = next_id()
                transcript.append(NegotiationTurn(
                    "CLARIFY", clarify_id, ref_id=last_id, dim=dim, candidates=(d.target, d.source),
                    question=f"{d.field}: receiver read '{d.target}', sender's own message implies "
                             f"'{d.source}' — which is correct?"))

                ans = await session.call_tool("answer", {"dim": dim})
                wire_value = json.loads(ans.content[0].text)["value"]
                sender_value = _coerce(belief.get(dim), wire_value)

                if dim == "actions" and _is_empty(sender_value):
                    rej_id = next_id()
                    transcript.append(NegotiationTurn(
                        "REJECT", rej_id, ref_id=clarify_id,
                        reason=f"sender's own message does not resolve {d.field} either — cannot "
                               f"confirm which reading is correct"))
                    return NegotiationOutcome(False, n, transcript, belief, result.differences)

                answer_id = next_id()
                transcript.append(NegotiationTurn(
                    "ANSWER", answer_id, ref_id=clarify_id, dim=dim, value=_fmt(sender_value)))
                belief[dim] = sender_value
                last_id = answer_id

            result = compare_canonical(sender_canonical, belief, cfg)
            if result.equivalent:
                acc_id = next_id()
                transcript.append(NegotiationTurn("ACCEPT", acc_id, ref_id=last_id))
                return NegotiationOutcome(True, n, transcript, belief, [])
            rej_id = next_id()
            transcript.append(NegotiationTurn(
                "REJECT", rej_id, ref_id=last_id,
                reason=f"no consensus after {max_rounds} rounds; {len(result.differences)} dimension(s) still differ"))
            return NegotiationOutcome(False, n, transcript, belief, result.differences)


def negotiate_autonomous(sender_command: list[str], receiver_canonical: dict, config: dict | None = None,
                          max_rounds: int = 3, msg_prefix: str = "M") -> NegotiationOutcome:
    """Spawn `sender_command` (a real `python -m aixl.agents.sender_agent ...` invocation) as a
    genuinely separate OS process and drive a full REQUEST -> CLARIFY -> ANSWER -> ACCEPT/REJECT
    exchange with it over real MCP stdio JSON-RPC. No human relays any turn. Mirrors
    `aixl.negotiation.negotiate`'s signature and return type (NegotiationOutcome)."""
    return asyncio.run(negotiate_autonomous_async(sender_command, receiver_canonical, config, max_rounds, msg_prefix))
