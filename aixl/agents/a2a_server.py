"""A REAL A2A agent exposing AIXL 0.3 over the actual Agent2Agent protocol (official `a2a-sdk`, JSON-RPC
over HTTP). Run it directly: `python -m aixl.agents.a2a_server [PORT]`. Any real A2A client (the SDK's
own `ClientFactory`, or another agent) can then call `aixl_compare`/`aixl_negotiate` over a real HTTP
round-trip — this is the piece that used to be `NotImplementedError` in
aixl/adapters/protocol_adapter.py (E-A2A, 2026-09-30), the counterpart of aixl/mcp_server.py for the A2A
protocol instead of MCP.

Exposes two skills:
- `aixl_compare`: immediate-response — a Message carrying `{"a": "...", "b": "..."}`, replied with
  `aixl.compare(a, b).to_dict()`.
- `aixl_negotiate`: a genuine multi-turn A2A TASK (E-A2A-NEGOTIATE, same day), not a single reply — see
  aixl/agents/a2a_negotiate.py for why and how; it pauses (TASK_STATE_INPUT_REQUIRED) and asks a human
  when, and only when, the disagreement involves an irreversible action.
No new negotiation semantics are introduced here; aixl/negotiation.py itself is untouched.

Production readiness (DevOps pass, 2026-10-01): `/healthz`/`/readyz`/`/metrics` routes (see
aixl/agents/observability.py), structured logging, and a container-friendly main() (PORT/host/public
URL all overridable by environment variables, not just the positional CLI arg) — see DEPLOYMENT.md for
the full deployment architecture, CI/CD pipeline, Docker/Kubernetes config and production checklist."""
import logging
import os
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
from aixl.agents.a2a_negotiate import start_negotiation, resume_negotiation
from aixl.agents.observability import configure_logging, inc, observability_routes

log = logging.getLogger("aixl.a2a_server")

SKILL_ID = "aixl_compare"
NEGOTIATE_SKILL_ID = "aixl_negotiate"


def _agent_card(url: str) -> AgentCard:
    return AgentCard(
        name="aixl-core",
        description="Compares two instructions (or AIXL messages) for semantic equivalence, "
                    "similarity, drift; negotiates disagreements, escalating to a human when an "
                    "irreversible action is in dispute.",
        version=aixl.__version__,
        supported_interfaces=[AgentInterface(url=url, protocol_binding="JSONRPC", protocol_version="1.0")],
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[
            AgentSkill(
                id=SKILL_ID, name="aixl_compare",
                description="Compare two instructions for semantic equivalence, similarity and drift.",
                tags=["semantics", "equivalence"], input_modes=["application/json"], output_modes=["application/json"],
            ),
            AgentSkill(
                id=NEGOTIATE_SKILL_ID, name="aixl_negotiate",
                description="Resolve a disagreement between a sender and a receiver instruction via a "
                            "bounded, multi-turn A2A Task; pauses and asks a human when the disagreement "
                            "involves an irreversible action.",
                tags=["semantics", "negotiation"], input_modes=["application/json"], output_modes=["application/json"],
            ),
        ],
    )


class AixlAgentExecutor(AgentExecutor):
    """`aixl_compare` is immediate-response-only (one reply Message, never a Task). `aixl_negotiate` is
    the one case this agent genuinely needs A2A's stateful Task model for — see a2a_negotiate.py."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        inc("aixl_requests_total")
        data_parts = get_data_parts(context.message.parts) if context.message else []
        req = data_parts[0] if data_parts else {}

        try:
            if context.current_task is not None:
                await resume_negotiation(context, event_queue, req)
                return
            if req.get("skill") == NEGOTIATE_SKILL_ID:
                inc("aixl_negotiate_started_total")
                await start_negotiation(context, event_queue, req)
                return

            inc("aixl_compare_total")
            result = aixl.compare(req.get("a", ""), req.get("b", "")).to_dict()
            reply = new_data_message(result, role=Role.ROLE_AGENT,
                                      context_id=context.context_id, task_id=context.task_id)
            await event_queue.enqueue_event(reply)
        except Exception:
            inc("aixl_errors_total")
            log.exception("execute() failed")
            raise

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise UnsupportedOperationError("aixl-core's A2A agent does not support cancelling a "
                                         "negotiation task mid-flight yet")


def build_app(url: str):
    from starlette.applications import Starlette

    card = _agent_card(url)
    handler = DefaultRequestHandler(AixlAgentExecutor(), InMemoryTaskStore(), card)
    routes = (observability_routes() + create_agent_card_routes(card)
              + create_jsonrpc_routes(handler, rpc_url="/"))
    return Starlette(routes=routes)


def main():
    import uvicorn

    configure_logging()
    port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else 8766))
    host = os.environ.get("AIXL_A2A_HOST", "127.0.0.1")
    public_url = os.environ.get("AIXL_A2A_PUBLIC_URL") or f"http://127.0.0.1:{port}/"
    app = build_app(public_url)
    log.info("starting aixl a2a agent on %s:%s (public url: %s)", host, port, public_url)
    uvicorn.run(app, host=host, port=port, log_level=os.environ.get("AIXL_LOG_LEVEL", "info").lower(),
                log_config=None)


if __name__ == "__main__":
    main()
