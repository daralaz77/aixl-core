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
from a2a.types.a2a_pb2 import Role, SendMessageRequest                # noqa: E402

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


def test_agent_card_lists_the_aixl_compare_skill(server_url):
    r = httpx.get(f"{server_url}/.well-known/agent-card.json")
    card = r.json()
    assert card["name"] == "aixl-core"
    assert {s["id"] for s in card["skills"]} == {"aixl_compare"}


def test_aixl_compare_over_real_a2a_jsonrpc_http_transport_detects_equivalence(server_url):
    result = asyncio.run(_compare(server_url, "Analiza las ventas de Q1 2026.",
                                   "Examina las ventas del primer trimestre de 2026."))
    assert result["equivalent"] is True
    assert result["drift_level"] == "NO_DRIFT"


def test_aixl_compare_over_real_a2a_jsonrpc_http_transport_detects_critical_negation_drift(server_url):
    result = asyncio.run(_compare(server_url, "Elimina el reporte.", "No elimines el reporte."))
    assert result["equivalent"] is False
    assert result["drift_level"] == "CRITICAL_DRIFT"
