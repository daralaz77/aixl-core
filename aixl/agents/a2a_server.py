"""A REAL A2A agent exposing AIXL 0.3 over the actual Agent2Agent protocol (official `a2a-sdk`, JSON-RPC
over HTTP). Run it directly: `python -m aixl.agents.a2a_server [PORT]`. Any real A2A client (the SDK's
own `ClientFactory`, or another agent) can then call `aixl_compare` over a real HTTP round-trip — this is
the piece that used to be `NotImplementedError` in aixl/adapters/protocol_adapter.py (E-A2A, 2026-09-30),
the counterpart of aixl/mcp_server.py for the A2A protocol instead of MCP.

Exposes one skill, `aixl_compare`: the request is a single A2A Message carrying a data Part
`{"a": "...", "b": "..."}`, the reply is a single A2A Message carrying a data Part with
`aixl.compare(a, b).to_dict()`. No new semantics are introduced here; this module is transport only,
same design note as aixl/mcp_server.py."""
import sys

from a2a.helpers.proto_helpers import get_data_parts, new_data_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types.a2a_pb2 import (
    AgentCapabilities, AgentCard, AgentInterface, AgentSkill, Role,
)
from a2a.utils.errors import UnsupportedOperationError

import aixl

SKILL_ID = "aixl_compare"


def _agent_card(url: str) -> AgentCard:
    return AgentCard(
        name="aixl-core",
        description="Compares two instructions (or AIXL messages) for semantic equivalence, "
                    "similarity, drift.",
        version=aixl.__version__,
        supported_interfaces=[AgentInterface(url=url, protocol_binding="JSONRPC", protocol_version="1.0")],
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[AgentSkill(
            id=SKILL_ID, name="aixl_compare",
            description="Compare two instructions for semantic equivalence, similarity and drift.",
            tags=["semantics", "equivalence"], input_modes=["application/json"], output_modes=["application/json"],
        )],
    )


class AixlAgentExecutor(AgentExecutor):
    """Immediate-response-only executor: `aixl.compare()` is fast and synchronous, so `execute()`
    computes the result and enqueues ONE reply Message — the "Immediate response" workflow the
    AgentExecutor contract documents, never a long-running Task."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        data_parts = get_data_parts(context.message.parts) if context.message else []
        req = data_parts[0] if data_parts else {}
        result = aixl.compare(req.get("a", ""), req.get("b", "")).to_dict()
        reply = new_data_message(result, role=Role.ROLE_AGENT,
                                  context_id=context.context_id, task_id=context.task_id)
        await event_queue.enqueue_event(reply)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise UnsupportedOperationError("aixl-core's A2A agent only does immediate, synchronous "
                                         "replies; there is no long-running task to cancel")


def build_app(url: str):
    from starlette.applications import Starlette

    card = _agent_card(url)
    handler = DefaultRequestHandler(AixlAgentExecutor(), InMemoryTaskStore(), card)
    routes = create_agent_card_routes(card) + create_jsonrpc_routes(handler, rpc_url="/")
    return Starlette(routes=routes)


def main():
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
    app = build_app(f"http://127.0.0.1:{port}/")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
