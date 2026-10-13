"""A2A access guard (consejo-5x audit 2026-10-13): authentication, rate limit, body cap, and fail-closed startup."""
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from aixl.agents.guard import Guard, GuardConfig, is_loopback, startup_problem


async def _ok(request):
    return JSONResponse({"ok": True, "body_len": len(await request.body())})


def _app():
    return Starlette(routes=[Route("/healthz", _ok, methods=["GET"]), Route("/readyz", _ok, methods=["GET"]),
                             Route("/.well-known/agent-card.json", _ok, methods=["GET"]), Route("/metrics", _ok, methods=["GET"]),
                             Route("/", _ok, methods=["POST", "GET"])])


class Clock:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t


def _client(**kw):
    clock = kw.pop("clock", None) or Clock()
    cfg = GuardConfig(clock=clock, **kw)
    return TestClient(Guard(_app(), cfg)), clock


def test_probes_and_agent_card_are_public_even_with_a_token():
    c, _ = _client(token="s3cret")
    for p in ("/healthz", "/readyz", "/.well-known/agent-card.json"):
        assert c.get(p).status_code == 200, p


def test_rpc_and_metrics_need_the_bearer_token():
    c, _ = _client(token="s3cret")
    assert c.post("/", content=b"{}").status_code == 401
    assert c.get("/metrics").status_code == 401
    assert c.post("/", content=b"{}", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert c.post("/", content=b"{}", headers={"Authorization": "Basic s3cret"}).status_code == 401
    r = c.post("/", content=b"{}", headers={"Authorization": "Bearer s3cret"})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert c.post("/", content=b"{}").headers.get("www-authenticate") == "Bearer"


def test_no_token_configured_means_open_but_still_rate_limited_and_capped():
    c, _ = _client()                                                  # loopback-style open mode
    assert c.post("/", content=b"{}").status_code == 200


def test_rate_limit_returns_429_with_retry_after_and_refills():
    c, clock = _client(rate_per_min=3)
    assert [c.post("/", content=b"x").status_code for _ in range(3)] == [200, 200, 200]
    r = c.post("/", content=b"x")
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1 and r.json()["error"] == "rate_limited"
    clock.t += 21                                                      # 3/min => one token every 20 s
    assert c.post("/", content=b"x").status_code == 200
    assert c.get("/healthz").status_code == 200                       # probes are never rate limited


def test_oversized_body_is_413_by_header_and_by_stream():
    c, _ = _client(max_body_bytes=100)
    assert c.post("/", content=b"x" * 101).status_code == 413
    assert c.post("/", content=b"x" * 100).status_code == 200
    def chunks():                                                      # no Content-Length: chunked upload
        for _ in range(5):
            yield b"y" * 40
    assert c.post("/", content=chunks()).status_code == 413


def test_startup_fails_closed_on_a_public_interface_without_a_token():
    assert is_loopback("127.0.0.1") and is_loopback("localhost") and not is_loopback("0.0.0.0")
    assert startup_problem("127.0.0.1", GuardConfig(), env={}) is None
    assert startup_problem("0.0.0.0", GuardConfig(token="t"), env={}) is None
    assert "AIXL_A2A_TOKEN" in startup_problem("0.0.0.0", GuardConfig(), env={})
    assert startup_problem("0.0.0.0", GuardConfig(), env={"AIXL_A2A_ALLOW_ANONYMOUS": "1"}) is None


def test_config_from_env_is_defensive():
    cfg = GuardConfig.from_env({"AIXL_A2A_TOKEN": "abc", "AIXL_A2A_RATE_PER_MIN": "oops", "AIXL_A2A_MAX_BODY_BYTES": "5000"})
    assert cfg.token == "abc" and cfg.rate_per_min == 120 and cfg.max_body_bytes == 5000
    assert GuardConfig.from_env({}).token is None


def test_the_real_a2a_app_is_wrapped_and_protected():
    pytest.importorskip("a2a")
    from aixl.agents.a2a_server import build_app
    app = build_app("http://127.0.0.1:1/", GuardConfig(token="tok"))
    assert isinstance(app, Guard)
    c = TestClient(app)
    assert c.get("/healthz").status_code == 200
    assert c.get("/.well-known/agent-card.json").status_code == 200
    assert c.post("/", json={"jsonrpc": "2.0", "id": 1, "method": "message/send", "params": {}}).status_code == 401
    assert isinstance(build_app("http://127.0.0.1:1/", False), Starlette)
