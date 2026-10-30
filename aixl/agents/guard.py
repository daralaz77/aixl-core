"""Access guard for the A2A HTTP agent (consejo-5x audit 2026-10-13, risk #5: the server had NO authentication and NO rate limit; k8s/compose
set AIXL_A2A_HOST=0.0.0.0). Pure ASGI, no dependency, testable without the A2A SDK.

  * Public (no token): /healthz, /readyz (probes) and the agent card (discovery). Everything else (JSON-RPC, /metrics) needs `Authorization: Bearer <token>`.
  * Fail closed: bound to a NON-loopback host with no token, the server refuses to start unless AIXL_A2A_ALLOW_ANONYMOUS=1 is set on purpose.
  * Rate limit: token bucket per client address (AIXL_A2A_RATE_PER_MIN, default 120); 429 + Retry-After. In-memory, per process: with N replicas the
    effective limit is N x that, and clients behind one proxy share a bucket.
  * Body cap: AIXL_A2A_MAX_BODY_BYTES (default 262144) -> 413, before the analysis-size guard (aixl.core.limits) is even reached."""
import hmac
import ipaddress
import json
import os
import time
from dataclasses import dataclass, field

MAX_TRACKED_CLIENTS = 10_000                      # rate-limit buckets kept in memory; beyond this, idle (fully refilled) ones are dropped
PUBLIC_PATHS = frozenset({"/healthz", "/readyz", "/.well-known/agent-card.json", "/.well-known/agent.json"})
_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})


def is_loopback(host: str) -> bool:
    if host in _LOOPBACK:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback          # a DNS name such as "127.example.com" is NOT loopback
    except ValueError:
        return False


@dataclass
class GuardConfig:
    token: str | None = None
    rate_per_min: int = 120
    max_body_bytes: int = 262_144
    public_paths: frozenset = PUBLIC_PATHS
    clock: object = field(default=time.monotonic, repr=False)

    @classmethod
    def from_env(cls, env=None) -> "GuardConfig":
        e = os.environ if env is None else env
        def num(name, default):
            try: return max(1, int(e.get(name, default)))
            except ValueError: return default
        return cls(token=(e.get("AIXL_A2A_TOKEN") or None), rate_per_min=num("AIXL_A2A_RATE_PER_MIN", 120), max_body_bytes=num("AIXL_A2A_MAX_BODY_BYTES", 262_144))


def startup_problem(host: str, cfg: GuardConfig, env=None) -> str | None:
    """Return why the server must not start (None = fine)."""
    e = os.environ if env is None else env
    if not is_loopback(host) and not cfg.token and e.get("AIXL_A2A_ALLOW_ANONYMOUS") != "1":
        return (f"refusing to listen on {host!r} without authentication: set AIXL_A2A_TOKEN (clients send `Authorization: Bearer <token>`), "
                f"or AIXL_A2A_ALLOW_ANONYMOUS=1 if this is an isolated network on purpose")
    return None


class Guard:
    def __init__(self, app, cfg: GuardConfig):
        self.app, self.cfg = app, cfg
        self._buckets: dict = {}                      # client -> [tokens, last_ts]

    # -- helpers ----------------------------------------------------------------------------------------------------
    @staticmethod
    async def _reply(send, status: int, body: dict, headers=()):
        payload = json.dumps(body).encode()
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(payload)).encode()), *headers]})
        await send({"type": "http.response.body", "body": payload})

    def _allow(self, client: str):
        """Token bucket. Returns (allowed, retry_after_seconds)."""
        now, cap = self.cfg.clock(), float(self.cfg.rate_per_min)
        if len(self._buckets) >= MAX_TRACKED_CLIENTS and client not in self._buckets:
            # a refilled bucket is indistinguishable from a new client, so dropping it changes no decision
            self._buckets = {c: b for c, b in self._buckets.items() if b[0] + (now - b[1]) * cap / 60.0 < cap}
        tokens, last = self._buckets.get(client, (cap, now))
        tokens = min(cap, tokens + (now - last) * cap / 60.0)
        if tokens >= 1.0:
            self._buckets[client] = (tokens - 1.0, now)
            return True, 0
        self._buckets[client] = (tokens, now)
        return False, max(1, int((1.0 - tokens) * 60.0 / cap) + 1)

    # -- ASGI -------------------------------------------------------------------------------------------------------
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path", "/") in self.cfg.public_paths:
            return await self.app(scope, receive, send)
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        if self.cfg.token:
            got = headers.get(b"authorization", b"")
            ok = got[:7].lower() == b"bearer " and hmac.compare_digest(got[7:].strip(), self.cfg.token.encode())
            if not ok:
                return await self._reply(send, 401, {"error": "unauthorized"}, [(b"www-authenticate", b"Bearer")])
        client = (scope.get("client") or ("unknown", 0))[0]
        allowed, retry = self._allow(client)
        if not allowed:
            return await self._reply(send, 429, {"error": "rate_limited", "retry_after_seconds": retry}, [(b"retry-after", str(retry).encode())])
        cl = headers.get(b"content-length")
        if cl and cl.isdigit() and int(cl) > self.cfg.max_body_bytes:
            return await self._reply(send, 413, {"error": "payload_too_large", "max_bytes": self.cfg.max_body_bytes})
        # Buffer the body here (memory bounded by the cap) instead of failing inside the app: an exception raised from `receive` is caught by the
        # framework's error middleware, which has already answered 500 by the time we could answer 413.
        msgs, size = [], 0
        while True:
            msg = await receive()
            msgs.append(msg)
            if msg["type"] != "http.request":
                break
            size += len(msg.get("body", b""))
            if size > self.cfg.max_body_bytes:
                return await self._reply(send, 413, {"error": "payload_too_large", "max_bytes": self.cfg.max_body_bytes})
            if not msg.get("more_body", False):
                break
        replay = iter(msgs)

        async def replayed_receive():
            try:
                return next(replay)
            except StopIteration:
                return await receive()                  # e.g. a later http.disconnect

        await self.app(scope, replayed_receive, send)
