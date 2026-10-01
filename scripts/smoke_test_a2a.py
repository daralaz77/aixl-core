"""Real smoke test for the built aixl-core A2A image, run by .github/workflows/docker-publish.yml
against a real running container (`docker run ...`) before the image is pushed anywhere — a Dockerfile
that builds does not mean the image works (found for real while building this pipeline: the first
image built fine and crashed on start with `ModuleNotFoundError: uvicorn`, since a2a-sdk[http-server]
does not pull in an ASGI server by itself). Also runnable by hand: `python scripts/smoke_test_a2a.py
[URL]` (default http://127.0.0.1:8766)."""
import asyncio
import sys

from a2a.client.client_factory import ClientFactory
from a2a.helpers.proto_helpers import get_data_parts, new_data_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest


async def main(url: str) -> None:
    factory = ClientFactory()
    client = await factory.create_from_url(url)
    try:
        msg = new_data_message({"a": "Elimina el reporte.", "b": "No elimines el reporte."}, role=Role.ROLE_USER)
        async for resp in client.send_message(SendMessageRequest(message=msg)):
            if resp.HasField("message"):
                r = get_data_parts(resp.message.parts)[0]
                assert r["equivalent"] is False and r["drift_level"] == "CRITICAL_DRIFT", r
                print("smoke test OK:", r["equivalent"], r["drift_level"])
                return
        raise AssertionError("agent never sent a message reply")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766"))
