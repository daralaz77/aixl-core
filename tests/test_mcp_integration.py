"""REAL end-to-end validation (E-MCP, 2026-09-30), not a mock: spawns aixl/mcp_server.py as an actual
subprocess and drives it with the OFFICIAL `mcp` SDK's own ClientSession over real stdio JSON-RPC — the
same code path any real MCP client (Claude Desktop, another agent) would use. This is what distinguishes
a REAL protocol adapter from one that merely matches the wire format on paper.

Skipped automatically if the `mcp` package (an optional dependency, see pyproject.toml) is not installed."""
import asyncio
import json
import os
import sys

import pytest

mcp = pytest.importorskip("mcp")
from mcp import ClientSession                                   # noqa: E402
from mcp.client.stdio import stdio_client, StdioServerParameters  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


async def _call(tool: str, args: dict) -> dict:
    params = StdioServerParameters(command=sys.executable, args=["-m", "aixl.mcp_server"], cwd=REPO_ROOT)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool(tool, args)
            return {"tool_names": [t.name for t in tools.tools],
                    "text": result.content[0].text if result.content else None}


def test_server_lists_the_four_aixl_tools():
    out = asyncio.run(_call("aixl_translate", {"text": "Analiza las ventas de Q1 2026."}))
    assert set(out["tool_names"]) == {"aixl_translate", "aixl_compare", "aixl_negotiate",
                                       "aixl_negotiate_autonomous"}


def test_aixl_translate_over_real_mcp_stdio_transport():
    out = asyncio.run(_call("aixl_translate", {"text": "Analiza las ventas de Q1 2026."}))
    payload = json.loads(out["text"])
    assert payload["aixl"].startswith("V:AIXL-0.3")
    assert payload["ambiguous"] is False


def test_aixl_compare_over_real_mcp_stdio_transport_detects_critical_negation_drift():
    out = asyncio.run(_call("aixl_compare", {"a": "Elimina el reporte.", "b": "No elimines el reporte."}))
    payload = json.loads(out["text"])
    assert payload["equivalent"] is False
    assert payload["drift_level"] == "CRITICAL_DRIFT"


def test_aixl_negotiate_over_real_mcp_stdio_transport_converges():
    out = asyncio.run(_call("aixl_negotiate", {
        "sender_text": "Close ticket #77.", "receiver_text": "Delete ticket #77.", "max_rounds": 3}))
    payload = json.loads(out["text"])
    assert payload["converged"] is True
    assert payload["remaining_differences"] == []


def test_aixl_negotiate_autonomous_over_real_mcp_makes_the_server_spawn_a_third_real_process():
    """E-AUTONOMOUS wired into the real server (2026-09-30): calling this ONE MCP tool over stdio
    makes aixl_server.py itself spawn a genuinely separate sender-agent subprocess and negotiate with
    it over real MCP — a real third-party MCP client can now trigger the full autonomous 2-process
    exchange with a single call, not just this project's own scripts."""
    out = asyncio.run(_call("aixl_negotiate_autonomous", {
        "sender_text": "Close ticket #77.", "receiver_text": "Delete ticket #77.", "max_rounds": 3}))
    payload = json.loads(out["text"])
    assert payload["converged"] is True
    assert payload["remaining_differences"] == []
    assert payload["transcript"][0].startswith("NEGOTIATE X=REQUEST")
    assert "PAYLOAD=" in payload["transcript"][0]
