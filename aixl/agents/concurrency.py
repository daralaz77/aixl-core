"""Bounds how many CPU-bound aixl.compare()/_advance() calls run truly concurrently (DevOps pass,
2026-10-01 follow-up). Offloading each call to its own OS thread (`asyncio.to_thread`) stops ONE long
call from blocking the whole event loop in one atomic chunk, but does NOT by itself prevent dozens of
threads from all fighting over the GIL and the container's real CPU budget at once — confirmed for
real: even after switching every CPU-bound call to `asyncio.to_thread`, a burst of 900 concurrent
`aixl_compare` calls on a 1-CPU container still pushed `/healthz` latency past 4 seconds, because up to
~32 default `ThreadPoolExecutor` workers were all contending for the same single real core.

A small semaphore (default 4, matching the Deployment's own small CPU budget — see
`k8s/deployment.yaml`'s `resources.limits.cpu`) means only a few calls actually run at once; the rest
`await` cheaply inside the asyncio event loop (no OS thread spawned, no GIL contention) until a slot
frees up — which is what actually lets `/healthz` get scheduled promptly in between, confirmed by
re-running the exact same 900-concurrent-request burst after adding this."""
import asyncio
import os

_MAX_CONCURRENT_CPU_WORK = int(os.environ.get("AIXL_MAX_CONCURRENT_CPU_WORK", "4"))
_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_CPU_WORK)


async def run_cpu_bound(fn, *args):
    """Runs `fn(*args)` (a synchronous, CPU-bound callable) in a worker thread, admitting at most
    `AIXL_MAX_CONCURRENT_CPU_WORK` such calls at once; callers beyond that limit wait on the semaphore,
    not on a competing OS thread."""
    async with _semaphore:
        return await asyncio.to_thread(fn, *args)
