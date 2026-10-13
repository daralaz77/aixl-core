"""Concurrent load + recovery test of the A2A server (audit loop step 8). Starts its own server on a free loopback port and measures, with REAL
JSON-RPC over HTTP (the a2a client), not a mock:
  1. N concurrent aixl_compare calls: success rate, p50/p95/p99 latency, throughput
  2. /healthz latency WHILE the server is saturated (the container health check must not time out under load)
  3. rate limit: a burst above AIXL_A2A_RATE_PER_MIN answers 429 (never hangs, never 5xx)
  4. oversized body -> 413 and the server stays up
  5. recovery: kill -9 the process, restart, service answers again; SIGTERM exits promptly
Exit code 1 if any check fails.   python scripts/load_test_a2a.py [--n 300] [--conc 40]"""
import argparse
import asyncio
import os
import signal
import socket
import statistics
import subprocess
import sys
import time

import httpx
from a2a.client.client_factory import ClientFactory
from a2a.helpers.proto_helpers import get_data_parts, new_data_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAIRS = [("Elimina el reporte.", "No elimines el reporte."), ("Analiza las ventas de Q1 2026.", "Examina las ventas del primer trimestre de 2026."),
         ("Delete the old backups and the logs.", "Delete the old backups."), ("Envía el informe a Ana y a Luis.", "Envía el informe a Ana.")]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]


def start(port: int, env_extra: dict) -> subprocess.Popen:
    env = {**os.environ, **env_extra}
    p = subprocess.Popen([sys.executable, "-m", "aixl.agents.a2a_server", str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    t0 = time.monotonic()
    while time.monotonic() - t0 < 20:
        try:
            if httpx.get(url + "/healthz", timeout=0.5).status_code == 200:
                return p
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    p.kill(); raise RuntimeError("server did not become ready")


async def one(url: str, pair) -> tuple[bool, float]:
    t = time.perf_counter()
    try:
        client = await ClientFactory().create_from_url(url)
        try:
            async for resp in client.send_message(SendMessageRequest(message=new_data_message({"a": pair[0], "b": pair[1]}, role=Role.ROLE_USER))):
                if resp.HasField("message"):
                    ok = "equivalent" in get_data_parts(resp.message.parts)[0]
                    return ok, time.perf_counter() - t
        finally:
            await client.close()
    except Exception:
        pass
    return False, time.perf_counter() - t


async def health_during(url: str, stop: asyncio.Event, out: list):
    async with httpx.AsyncClient(timeout=10) as c:
        while not stop.is_set():
            t = time.perf_counter()
            try:
                r = await c.get(url + "/healthz"); out.append((r.status_code == 200, time.perf_counter() - t))
            except Exception:
                out.append((False, time.perf_counter() - t))
            await asyncio.sleep(0.05)


def pct(xs, q):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else float("nan")


async def load(url: str, n: int, conc: int):
    sem = asyncio.Semaphore(conc); res = []
    async def run(i):
        async with sem:
            res.append(await one(url, PAIRS[i % len(PAIRS)]))
    stop, health = asyncio.Event(), []
    h = asyncio.create_task(health_during(url, stop, health))
    t0 = time.perf_counter()
    await asyncio.gather(*(run(i) for i in range(n)))
    wall = time.perf_counter() - t0
    stop.set(); await h
    return res, health, wall


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=300); ap.add_argument("--conc", type=int, default=40)
    a = ap.parse_args()
    fails = []
    port = free_port(); url = f"http://127.0.0.1:{port}"
    proc = start(port, {"AIXL_A2A_RATE_PER_MIN": "100000"})
    try:
        res, health, wall = asyncio.run(load(url, a.n, a.conc))
        lat = [t for ok, t in res if ok]; okn = sum(ok for ok, _ in res)
        print(f"[1] {okn}/{a.n} ok, concurrency {a.conc}, wall {wall:.1f}s, {a.n / wall:.1f} req/s; latency p50 {pct(lat, .5)*1000:.0f} ms, p95 {pct(lat, .95)*1000:.0f} ms, p99 {pct(lat, .99)*1000:.0f} ms")
        if okn != a.n: fails.append(f"only {okn}/{a.n} succeeded")
        hl = [t for ok, t in health]; hok = sum(ok for ok, _ in health)
        print(f"[2] /healthz during load: {hok}/{len(health)} ok, p50 {pct(hl, .5)*1000:.0f} ms, p99 {pct(hl, .99)*1000:.0f} ms, max {max(hl)*1000:.0f} ms")
        if hok != len(health) or max(hl) > 3.0: fails.append("healthz degraded under load (>3 s or non-200)")
        # 4. body cap
        r = httpx.post(url + "/", content=b"x" * 400_000, timeout=10)
        print(f"[4] 400 kB body -> {r.status_code}"); 
        if r.status_code != 413: fails.append(f"oversized body gave {r.status_code}, expected 413")
        if httpx.get(url + "/healthz", timeout=3).status_code != 200: fails.append("server unhealthy after oversized body")
        # 5. recovery
        proc.send_signal(signal.SIGKILL); proc.wait(5)
        try: httpx.get(url + "/healthz", timeout=1); fails.append("server still answering after kill -9")
        except httpx.HTTPError: pass
        t0 = time.perf_counter(); proc = start(port, {"AIXL_A2A_RATE_PER_MIN": "100000"}); back = time.perf_counter() - t0
        ok, _ = asyncio.run(one(url, PAIRS[0]))
        print(f"[5] kill -9 -> restarted and answering in {back:.1f}s, compare ok={ok}")
        if not ok: fails.append("no correct answer after restart")
        t0 = time.perf_counter(); proc.send_signal(signal.SIGTERM)
        try: code = proc.wait(10)
        except subprocess.TimeoutExpired: code = None
        print(f"[5] SIGTERM -> exit code {code} in {time.perf_counter() - t0:.1f}s")
        if code is None: fails.append("SIGTERM did not stop the server within 10 s"); proc.kill()
    finally:
        if proc.poll() is None: proc.kill()
    # 3. rate limit (separate server with a tiny bucket)
    port = free_port(); url = f"http://127.0.0.1:{port}"
    proc = start(port, {"AIXL_A2A_RATE_PER_MIN": "20"})
    try:
        codes = [httpx.post(url + "/", json={"jsonrpc": "2.0", "id": i, "method": "x"}, timeout=10).status_code for i in range(60)]
        n429 = codes.count(429); n5 = sum(c >= 500 for c in codes)
        print(f"[3] 60-request burst at 20/min: {n429} x 429, {n5} x 5xx, other {len(codes) - n429 - n5}")
        if n429 == 0 or n5: fails.append(f"rate limit: {n429} 429s, {n5} 5xx")
    finally:
        proc.kill()
    print("LOAD TEST OK" if not fails else "LOAD TEST FAILED:\n  " + "\n  ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
