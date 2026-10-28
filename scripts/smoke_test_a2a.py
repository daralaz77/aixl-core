"""Real smoke test for the built aixl-core A2A image, run by .github/workflows/docker-publish.yml
against a real running container (`docker run ...`) before the image is pushed anywhere — a Dockerfile
that builds does not mean the image works (found for real while building this pipeline: the first
image built fine and crashed on start with `ModuleNotFoundError: uvicorn`, since a2a-sdk[http-server]
does not pull in an ASGI server by itself). Also runnable by hand: `python scripts/smoke_test_a2a.py
[URL]` (default http://127.0.0.1:8766); if AIXL_A2A_TOKEN is set in the environment the client sends it as a Bearer token.

Covers both skills, not just aixl_compare (an earlier version of this script only checked aixl_compare —
it would have missed a regression in aixl_negotiate entirely before publishing). Only the ordinary,
single-call auto-resolve path is checked here, not the pause/resume multi-turn flow: a CI smoke test
runs unattended, with no human to answer a paused CLARIFY question."""
import asyncio
import os
import sys

import httpx
from a2a.client import ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.helpers.proto_helpers import get_data_parts, new_data_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest


def _factory(token: str | None) -> ClientFactory:
    """The agent refuses to listen on a public interface without AIXL_A2A_TOKEN (2026-10-13), so a container started for this test has a token and the
    client must send it as `Authorization: Bearer <token>` (the agent card and /healthz stay public)."""
    if not token:
        return ClientFactory()
    return ClientFactory(ClientConfig(httpx_client=httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=30)))


async def check_auth(url: str, token: str | None) -> None:
    """With a token configured the guard must be ACTIVE in the image: an anonymous JSON-RPC call is rejected, the public probes are not."""
    async with httpx.AsyncClient(timeout=10) as c:
        assert (await c.get(url.rstrip("/") + "/healthz")).status_code == 200, "healthz must stay public"
        if token:
            r = await c.post(url, json={"jsonrpc": "2.0", "id": 1, "method": "message/send", "params": {}})
            assert r.status_code == 401, f"anonymous call was not rejected: {r.status_code}"
            print("smoke test OK (auth): anonymous JSON-RPC rejected with 401, /healthz public")


async def check_compare(url: str, token: str | None = None) -> None:
    factory = _factory(token)
    client = await factory.create_from_url(url)
    try:
        msg = new_data_message({"a": "Elimina el reporte.", "b": "No elimines el reporte."}, role=Role.ROLE_USER)
        async for resp in client.send_message(SendMessageRequest(message=msg)):
            if resp.HasField("message"):
                r = get_data_parts(resp.message.parts)[0]
                assert r["equivalent"] is False and r["drift_level"] == "CRITICAL_DRIFT", r
                print("smoke test OK (aixl_compare):", r["equivalent"], r["drift_level"])
                return
        raise AssertionError("agent never sent a message reply")
    finally:
        await client.close()


async def check_negotiate(url: str, token: str | None = None) -> None:
    factory = _factory(token)
    client = await factory.create_from_url(url)
    try:
        msg = new_data_message({"skill": "aixl_negotiate", "sender_text": "Archive ticket #77.",
                                 "receiver_text": "Update ticket #77.", "max_rounds": 3}, role=Role.ROLE_USER)
        async for resp in client.send_message(SendMessageRequest(message=msg)):
            if resp.HasField("task"):
                payload = get_data_parts(resp.task.status.message.parts)[0]
                assert resp.task.status.state == 3, resp.task.status.state  # TASK_STATE_COMPLETED
                assert payload["converged"] is True, payload
                print("smoke test OK (aixl_negotiate):", payload["converged"])
                return
        raise AssertionError("agent never sent a task reply")
    finally:
        await client.close()


async def main(url: str, token: str | None = None) -> None:
    await check_auth(url, token)
    await check_compare(url, token)
    await check_negotiate(url, token)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766", os.environ.get("AIXL_A2A_TOKEN") or None))
