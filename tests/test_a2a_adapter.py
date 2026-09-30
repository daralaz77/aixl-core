"""A2AAdapter (E-A2A, 2026-09-30): validates against the REAL protobuf models of the official `a2a-sdk`
(Google's Agent2Agent Python SDK), not a hand-rolled shape guess. See test_a2a_integration.py for the
real subprocess + real HTTP round-trip.

Skipped automatically if the `a2a` package (an optional dependency) is not installed."""
import pytest

pytest.importorskip("a2a")

import aixl
from aixl.adapters.protocol_adapter import A2AAdapter, A2AAdapterError


def test_encode_produces_a_real_a2a_message_shape():
    g = aixl.to_semantic("Analiza las ventas de Q1 2026.")
    payload = A2AAdapter().encode(g)
    assert payload["role"] == "ROLE_AGENT"
    assert payload["parts"][0]["text"].startswith("V:AIXL-0.3")
    assert "messageId" in payload


def test_decode_round_trips_the_graph():
    g = aixl.to_semantic("Analiza las ventas de Q1 2026.")
    adapter = A2AAdapter()
    g2 = adapter.decode(adapter.encode(g))
    assert g.canonical() == g2.canonical()


def test_decode_rejects_payload_with_no_text_part():
    with pytest.raises(A2AAdapterError):
        A2AAdapter().decode({"parts": [{"data": {"a": 1}}]})


def test_validate_accepts_a_well_formed_message():
    g = aixl.to_semantic("Elimina el reporte.")
    payload = A2AAdapter().encode(g)
    assert A2AAdapter().validate(payload) == []


def test_validate_rejects_non_dict_payload():
    errs = A2AAdapter().validate("not a dict")
    assert errs and "dict" in errs[0]


def test_validate_uses_the_real_a2a_sdk_protobuf_model_to_catch_a_malformed_envelope():
    # 'role' must be one of the real Role enum names per the actual Message proto — this string isn't one.
    errs = A2AAdapter().validate({"role": "NOT_A_REAL_ROLE", "parts": [{"text": "V:AIXL-0.3"}]})
    assert errs and "invalid A2A Message envelope" in errs[0]


def test_validate_rejects_a_well_formed_envelope_with_no_text_part():
    errs = A2AAdapter().validate({"role": "ROLE_AGENT", "parts": [{"data": {"a": 1}}]})
    assert errs and "no text Part" in errs[0]


def test_validate_catches_a_well_formed_envelope_carrying_broken_aixl():
    errs = A2AAdapter().validate({"role": "ROLE_AGENT", "parts": [{"text": "not valid aixl!!"}]})
    assert errs and "does not decode" in errs[0]
