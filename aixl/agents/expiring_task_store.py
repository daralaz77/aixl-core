"""Wraps a2a-sdk's InMemoryTaskStore with a TTL sweep (found by continuing to test the DevOps pass,
2026-10-01): `InMemoryTaskStore` never evicts anything. Measured for real: 200 real `aixl_negotiate`
tasks started and abandoned (paused at `TASK_STATE_INPUT_REQUIRED`, never resumed — exactly what a
human who never answers the CLARIFY question looks like) grew the running agent's memory from ~60MB to
~71MB with no way back down. That is unbounded, real resource-exhaustion risk for a reachable endpoint,
not a hypothetical one — at the k8s Deployment's 256Mi memory limit, roughly a few thousand abandoned
negotiations would OOMKill the pod.

`ExpiringTaskStore` deletes a task once it has gone untouched for longer than `AIXL_TASK_TTL_SECONDS`
(default 1 hour) — long enough for a real human to actually read and answer a paused CLARIFY question,
short enough to bound memory growth under abuse, a buggy client that never resumes, or simple churn."""
import os
import time

from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.tasks.task_store import TaskStore
from a2a.types.a2a_pb2 import ListTasksRequest, ListTasksResponse, Task

from aixl.agents.observability import inc

DEFAULT_TTL_SECONDS = 3600.0


class ExpiringTaskStore(TaskStore):
    def __init__(self, ttl_seconds: float | None = None):
        self._inner = InMemoryTaskStore()
        self._ttl = ttl_seconds if ttl_seconds is not None else float(
            os.environ.get("AIXL_TASK_TTL_SECONDS", DEFAULT_TTL_SECONDS))
        self._last_touched: dict[str, float] = {}

    async def save(self, task: Task, context) -> None:
        await self._inner.save(task, context)
        self._last_touched[task.id] = time.monotonic()
        await self._sweep(context)

    async def get(self, task_id: str, context) -> Task | None:
        return await self._inner.get(task_id, context)

    async def list(self, params: ListTasksRequest, context) -> ListTasksResponse:
        return await self._inner.list(params, context)

    async def delete(self, task_id: str, context) -> None:
        await self._inner.delete(task_id, context)
        self._last_touched.pop(task_id, None)

    async def _sweep(self, context) -> None:
        """Opportunistic sweep on every save() — no background task/timer needed for the volume this
        agent actually sees, and it means the TTL is enforced exactly when memory would otherwise grow
        (a new task being saved), not on an arbitrary separate schedule."""
        now = time.monotonic()
        expired = [tid for tid, ts in self._last_touched.items() if now - ts > self._ttl]
        for tid in expired:
            await self.delete(tid, context)
            inc("aixl_negotiate_expired_total")
