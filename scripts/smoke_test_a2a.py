"""Real smoke test for the built aixl-core A2A image, run by .github/workflows/docker-publish.yml
against a real running container (`docker run ...`) before the image is pushed anywhere — a Dockerfile
that builds does not mean the image works (found for real while building this pipeline: the first
image built fine and crashed on start with `ModuleNotFoundError: uvicorn`, since a2a-sdk[http-server]
does not pull in an ASGI server by itself). Also runnable by hand: `python scripts/smoke_test_a2a.py
[URL]` (default http://127.0.0.1:8766).

Covers both skills, not just aixl_compare (an earlier version of this script only checked aixl_compare —
it would have missed a regression in aixl_negotiate entirely before publishing). Only the ordinary,
single-call auto-resolve path is checked here, not the pause/resume multi-turn flow: a CI smoke test
runs unattended, with no human to answer a paused CLARIFY question."""
import asyncio
import sys

from a2a.client.client_factory import ClientFactory
from a2a.helpers.proto_helpers import get_data_parts, new_data_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest


async def check_compare(url: str) -> None:
    factory = ClientFactory()
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


async def check_negotiate(url: str) -> None:
    factory = ClientFactory()
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


async def main(url: str) -> None:
    await check_compare(url)
    await check_negotiate(url)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766"))
