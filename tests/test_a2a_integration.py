"""REAL end-to-end validation (E-A2A, 2026-09-30), not a mock: spawns aixl/agents/a2a_server.py as an
actual subprocess (real HTTP server, real listening socket) and drives it with the OFFICIAL `a2a-sdk`'s
own ClientFactory over a real JSON-RPC/HTTP round-trip — the same code path any real A2A client (another
agent, the SDK's own tooling) would use. This is what distinguishes a REAL protocol adapter from one that
merely matches the wire format on paper — same standard as tests/test_mcp_integration.py.

Skipped automatically if the `a2a` package (an optional dependency, see pyproject.toml) is not installed."""
import asyncio
import os
import socket
import subprocess
import sys
import time

import pytest

a2a = pytest.importorskip("a2a")
import httpx                                                        # noqa: E402
from a2a.client.client_factory import ClientFactory                  # noqa: E402
from a2a.helpers.proto_helpers import get_data_parts, new_data_message  # noqa: E402
from a2a.types.a2a_pb2 import Role, SendMessageRequest, TaskState     # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server_url():
    port = _free_port()
    proc = subprocess.Popen([sys.executable, "-m", "aixl.agents.a2a_server", str(port)], cwd=REPO_ROOT)
    url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{url}/.well-known/agent-card.json", timeout=0.5)
            if r.status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("aixl.agents.a2a_server did not become ready in time")
    yield url
    proc.terminate()
    proc.wait(timeout=5)


async def _compare(url: str, a: str, b: str) -> dict:
    factory = ClientFactory()
    client = await factory.create_from_url(url)
    try:
        req = SendMessageRequest(message=new_data_message({"a": a, "b": b}, role=Role.ROLE_USER))
        async for resp in client.send_message(req):
            if resp.HasField("message"):
                return get_data_parts(resp.message.parts)[0]
    finally:
        await client.close()
    raise AssertionError("agent never sent a message reply")


async def _negotiate(url: str, sender_text: str, receiver_text: str, max_rounds: int = 3):
    factory = ClientFactory()
    client = await factory.create_from_url(url)
    try:
        msg = new_data_message({"skill": "aixl_negotiate", "sender_text": sender_text,
                                 "receiver_text": receiver_text, "max_rounds": max_rounds}, role=Role.ROLE_USER)
        async for resp in client.send_message(SendMessageRequest(message=msg)):
            if resp.HasField("task"):
                return resp.task
    finally:
        await client.close()
    raise AssertionError("agent never sent a task reply")


async def _answer(url: str, task, value: str):
    factory = ClientFactory()
    client = await factory.create_from_url(url)
    try:
        msg = new_data_message({"value": value}, role=Role.ROLE_USER,
                                context_id=task.context_id, task_id=task.id)
        async for resp in client.send_message(SendMessageRequest(message=msg)):
            if resp.HasField("task"):
                return resp.task
    finally:
        await client.close()
    raise AssertionError("agent never sent a task reply")


def test_agent_card_lists_both_skills(server_url):
    r = httpx.get(f"{server_url}/.well-known/agent-card.json")
    card = r.json()
    assert card["name"] == "aixl-core"
    assert {s["id"] for s in card["skills"]} == {"aixl_compare", "aixl_negotiate"}


def test_aixl_compare_over_real_a2a_jsonrpc_http_transport_detects_equivalence(server_url):
    result = asyncio.run(_compare(server_url, "Analiza las ventas de Q1 2026.",
                                   "Examina las ventas del primer trimestre de 2026."))
    assert result["equivalent"] is True
    assert result["drift_level"] == "NO_DRIFT"


def test_aixl_compare_over_real_a2a_jsonrpc_http_transport_detects_critical_negation_drift(server_url):
    result = asyncio.run(_compare(server_url, "Elimina el reporte.", "No elimines el reporte."))
    assert result["equivalent"] is False
    assert result["drift_level"] == "CRITICAL_DRIFT"


def test_aixl_negotiate_over_real_a2a_resolves_an_ordinary_disagreement_in_one_call_no_pause(server_url):
    """A non-irreversible disagreement must auto-resolve immediately — the Task completes in the
    very first call, no TASK_STATE_INPUT_REQUIRED pause, exactly like negotiate()'s own behavior."""
    async def run():
        return await _negotiate(server_url, "Archive ticket #77.", "Update ticket #77.")
    task = asyncio.run(run())
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    payload = get_data_parts(task.status.message.parts)[0]
    assert payload["converged"] is True


def test_aixl_negotiate_over_real_a2a_pauses_for_a_human_on_an_irreversible_action_disagreement(server_url):
    """The real, multi-turn case this whole mechanism exists for: "Close ticket #77." (UPDATE) vs
    "Delete ticket #77." (DELETE) must PAUSE the Task (TASK_STATE_INPUT_REQUIRED) and ask a human —
    not silently trust either side — because DELETE is on data/config.json's irreversible_actions."""
    async def run():
        return await _negotiate(server_url, "Close ticket #77.", "Delete ticket #77.")
    task = asyncio.run(run())
    assert task.status.state == TaskState.TASK_STATE_INPUT_REQUIRED
    payload = get_data_parts(task.status.message.parts)[0]
    assert set(payload["candidates"]) == {"DELETE", "UPDATE"}
    assert payload["field"] == "actions"


def test_aixl_negotiate_over_real_a2a_resumes_and_converges_on_the_humans_answer(server_url):
    """A genuine multi-turn round-trip: pause, then a SECOND real HTTP call referencing the same
    task_id/context_id resumes it — the human's answer becomes the agreed value on BOTH sides."""
    async def run():
        task = await _negotiate(server_url, "Close ticket #77.", "Delete ticket #77.")
        return await _answer(server_url, task, "DELETE")
    task = asyncio.run(run())
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    payload = get_data_parts(task.status.message.parts)[0]
    assert payload["converged"] is True
    assert payload["canonical"]["actions"] == ["DELETE"]


def test_aixl_negotiate_over_real_a2a_resumes_on_the_other_candidate_too(server_url):
    """Proves the human's choice genuinely drives the outcome, not a hardcoded default: picking the
    OTHER candidate (UPDATE, the sender's original reading) must converge to UPDATE, not DELETE."""
    async def run():
        task = await _negotiate(server_url, "Close ticket #77.", "Delete ticket #77.")
        return await _answer(server_url, task, "UPDATE")
    task = asyncio.run(run())
    payload = get_data_parts(task.status.message.parts)[0]
    assert payload["canonical"]["actions"] == ["UPDATE"]


def test_aixl_negotiate_over_real_a2a_rejects_immediately_when_sender_resolves_nothing(server_url):
    """"Quita el ticket #77." is out-of-vocabulary for the sender's own actions — must REJECT outright
    ("does not resolve"), not pause and ask a human to pick between DELETE and NOT_SPECIFIED. Order of
    the empty-check vs the irreversible-check matters here (see a2a_negotiate.py's own regression note)."""
    async def run():
        return await _negotiate(server_url, "Quita el ticket #77.", "Elimina el ticket #77.")
    task = asyncio.run(run())
    assert task.status.state == TaskState.TASK_STATE_REJECTED
    payload = get_data_parts(task.status.message.parts)[0]
    assert payload["converged"] is False
    assert "does not resolve" in payload["reason"]


def test_healthz_reports_ok_over_real_http(server_url):
    r = httpx.get(f"{server_url}/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_readyz_reports_ready_over_real_http(server_url):
    r = httpx.get(f"{server_url}/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_metrics_is_real_prometheus_text_format_and_counts_a_real_compare_call(server_url):
    before = httpx.get(f"{server_url}/metrics").text
    before_n = int([l for l in before.splitlines() if l.startswith("aixl_compare_total")][0].split()[1])

    asyncio.run(_compare(server_url, "Analiza las ventas de Q1 2026.",
                          "Examina las ventas del primer trimestre de 2026."))

    after = httpx.get(f"{server_url}/metrics").text
    assert "# TYPE aixl_requests_total counter" in after
    after_n = int([l for l in after.splitlines() if l.startswith("aixl_compare_total")][0].split()[1])
    assert after_n == before_n + 1
