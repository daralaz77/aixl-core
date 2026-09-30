"""E-AUTONOMOUS (2026-09-30): a REAL negotiation between two SEPARATE OS processes over stdio
JSON-RPC, no human relaying turns — proves aixl/autonomous_negotiation.py against
aixl/negotiation.py's already-tested `negotiate()` on the same inputs (parity), and against a real
spawned subprocess (not a mock). Skipped automatically if the optional `mcp` dependency isn't
installed (same convention as tests/test_mcp_integration.py)."""
import sys

import pytest

mcp = pytest.importorskip("mcp")

from aixl import negotiation as neg                       # noqa: E402
from aixl.autonomous_negotiation import negotiate_autonomous, _sender_env_and_cwd  # noqa: E402
from aixl.translators.natural_to_semantic import to_graph  # noqa: E402


def _sender_cmd(text: str) -> list[str]:
    return [sys.executable, "-m", "aixl.agents.sender_agent", "--text", text]


def test_autonomous_negotiation_converges_archive_update_ticket_case():
    # DISABLE vs UPDATE, not DELETE — see test_autonomous_negotiation_rejects_an_irreversible_action_case
    # below for why Close/Delete (UPDATE vs DELETE) stopped being a plain-convergence example after
    # E-MCP's irreversible-action REJECT fix (2026-09-30).
    receiver_canonical = to_graph("Update ticket #77.").canonical()
    out = negotiate_autonomous(_sender_cmd("Archive ticket #77."), receiver_canonical, max_rounds=3)
    assert out.converged is True
    assert out.remaining_differences == []
    assert out.transcript[1].dim == "actions"
    assert out.transcript[2].value == "DISABLE"


def test_autonomous_negotiation_rejects_an_irreversible_action_case():
    # the real case a genuine third-party MCP client (Claude Desktop, E-MCP, 2026-09-30) surfaced:
    # "Close ticket #77." (UPDATE) vs "Delete ticket #77." (DELETE) must REJECT, not silently ACCEPT on
    # the sender's say-so, since DELETE is irreversible and a wrong guess can't be undone.
    receiver_canonical = to_graph("Delete ticket #77.").canonical()
    out = negotiate_autonomous(_sender_cmd("Close ticket #77."), receiver_canonical, max_rounds=3)
    assert out.converged is False
    assert out.transcript[-1].turn_type == "REJECT"
    assert "irreversible action" in out.transcript[-1].reason


def test_autonomous_negotiation_matches_single_process_negotiate_on_the_same_case():
    """Parity check: the same inputs must resolve to the same outcome whether negotiate() runs it
    in one process (a local dict lookup) or negotiate_autonomous() asks a real separate process."""
    sender_canonical = to_graph("Close ticket #77.").canonical()
    receiver_canonical = to_graph("Delete ticket #77.").canonical()
    manual = neg.negotiate(sender_canonical, receiver_canonical, max_rounds=3)
    auto = negotiate_autonomous(_sender_cmd("Close ticket #77."), receiver_canonical, max_rounds=3)
    assert auto.converged == manual.converged
    assert [t.turn_type for t in auto.transcript] == [t.turn_type for t in manual.transcript]
    assert auto.remaining_differences == manual.remaining_differences


def test_autonomous_negotiation_rejects_when_sender_cannot_resolve_actions():
    """Same real bug case as test_negotiation.py's non-autonomous version, now over a real subprocess:
    an out-of-vocabulary sender verb ('quita') must REJECT, not silently discard the receiver's
    plausibly-correct DELETE reading."""
    receiver_canonical = to_graph("Elimina el ticket #77.").canonical()
    out = negotiate_autonomous(_sender_cmd("Quita el ticket #77."), receiver_canonical, max_rounds=3)
    assert out.converged is False
    assert out.transcript[-1].turn_type == "REJECT"
    assert any(d.field == "ACTION" for d in out.remaining_differences)


def test_autonomous_negotiation_request_turn_carries_the_real_transmitted_payload():
    """Unlike negotiate() (whose REQUEST turn never carried a payload, since both canonical forms
    were already known to the single caller), the autonomous REQUEST must carry the sender's actual
    AIXL line as received over the wire — proof the receiver didn't already have it out-of-band."""
    receiver_canonical = to_graph("Delete ticket #77.").canonical()
    out = negotiate_autonomous(_sender_cmd("Close ticket #77."), receiver_canonical, max_rounds=3)
    assert out.transcript[0].turn_type == "REQUEST"
    assert out.transcript[0].payload.startswith("V:AIXL-0.3")
    assert "A:UPDATE" in out.transcript[0].payload


def test_sender_env_always_includes_pythonpath_even_when_the_current_process_lacks_it(monkeypatch):
    """Real bug (2026-09-30, found by a real MCP client — Claude Desktop — failing where every one
    of this project's own manual reproductions succeeded): when negotiate_autonomous_async runs
    INSIDE an MCP server that a host app itself launched with a minimal, replaced `env` (typically
    just {"PYTHONPATH": ...}), the `mcp` SDK's default env-inheritance for the NESTED sender-agent
    spawn (mcp.client.stdio.DEFAULT_INHERITED_ENV_VARS = HOME/LOGNAME/PATH/SHELL/TERM/USER) does NOT
    include PYTHONPATH — so relying on it silently drops the one variable the nested `import aixl`
    needs. Fixed by building the nested child's env explicitly rather than depending on inheritance
    across two layers of MCP process spawning."""
    monkeypatch.delenv("PYTHONPATH", raising=False)
    env, cwd = _sender_env_and_cwd()
    assert "PYTHONPATH" in env
    assert env["PYTHONPATH"].endswith("aixl-core")
    assert cwd.endswith("aixl-core")


def test_autonomous_negotiation_sender_replay_mode_accepts_a_precomputed_aixl_line():
    """--aixl mode: the sender agent replays an already-encoded AIXL line instead of a raw text —
    the real mode used to re-run genuine historical E-INTEROP disagreements (see
    benchmarks/autonomous_negotiation_eval.py) without needing a live model call."""
    # A:UPDATE vs A:DISABLE, not A:DELETE/EXECUTE/SEND — those trigger E-MCP's irreversible-action
    # REJECT (2026-09-30, widened to EXECUTE/SEND the same day), which isn't what replay mode itself
    # is testing here.
    from aixl.serialization import aixl_codec
    sender_aixl = "V:AIXL-0.3 I:REQUEST_EXECUTION A:UPDATE Y:#77"
    cmd = [sys.executable, "-m", "aixl.agents.sender_agent", "--aixl", sender_aixl]
    receiver_canonical = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_EXECUTION A:DISABLE Y:#77").canonical()
    out = negotiate_autonomous(cmd, receiver_canonical, max_rounds=3)
    assert out.converged is True
    assert out.transcript[0].payload == sender_aixl
