"""ExpiringTaskStore (found 2026-10-01 by continuing to load-test the DevOps pass): a2a-sdk's own
InMemoryTaskStore never evicts anything — confirmed for real that 200 abandoned (paused, never resumed)
aixl_negotiate tasks grew the running agent's memory from ~60MB to ~71MB with no way back down. These
are fast unit tests against the store directly (no Docker/HTTP needed) proving the TTL sweep actually
bounds growth without breaking a task that's still within its TTL.

Skipped automatically if the `a2a` package (an optional dependency) is not installed."""
import asyncio

import pytest

pytest.importorskip("a2a")

from a2a.helpers.proto_helpers import new_task  # noqa: E402
from a2a.server.context import ServerCallContext  # noqa: E402
from a2a.types.a2a_pb2 import TaskState  # noqa: E402

from aixl.agents.expiring_task_store import ExpiringTaskStore  # noqa: E402


def _task(task_id: str):
    return new_task(task_id, context_id=f"ctx-{task_id}", state=TaskState.TASK_STATE_INPUT_REQUIRED)


def test_a_task_within_ttl_is_still_gettable():
    async def run():
        store = ExpiringTaskStore(ttl_seconds=60)
        await store.save(_task("t1"), context=ServerCallContext())
        return await store.get("t1", context=ServerCallContext())
    assert asyncio.run(run()) is not None


def test_a_task_past_ttl_is_swept_on_the_next_save():
    async def run():
        store = ExpiringTaskStore(ttl_seconds=0.05)
        await store.save(_task("stale"), context=ServerCallContext())
        before = await store.get("stale", context=ServerCallContext())   # not swept yet -- no save() since
        await asyncio.sleep(0.1)   # now past the 0.05s TTL
        await store.save(_task("trigger-sweep"), context=ServerCallContext())   # sweep runs as a side effect of save()
        after = await store.get("stale", context=ServerCallContext())
        return before, after
    before, after = asyncio.run(run())
    assert before is not None
    assert after is None


def test_sweeping_a_stale_task_does_not_touch_an_unrelated_fresh_one():
    async def run():
        store = ExpiringTaskStore(ttl_seconds=0.05)
        await store.save(_task("stale"), context=ServerCallContext())
        await asyncio.sleep(0.1)   # "stale" is now past its TTL; "fresh" below is not
        await store.save(_task("fresh"), context=ServerCallContext())   # this save's own sweep removes "stale", not itself
        return await store.get("fresh", context=ServerCallContext())
    assert asyncio.run(run()) is not None


def test_explicit_delete_also_clears_the_internal_timestamp_bookkeeping():
    async def run():
        store = ExpiringTaskStore(ttl_seconds=60)
        await store.save(_task("t1"), context=ServerCallContext())
        await store.delete("t1", context=ServerCallContext())
        return store, await store.get("t1", context=ServerCallContext())
    store, result = asyncio.run(run())
    assert "t1" not in store._last_touched
    assert result is None
