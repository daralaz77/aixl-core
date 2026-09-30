"""MCPAdapter (E-MCP, 2026-09-30): validates against the REAL pydantic models of the official `mcp` SDK,
not a hand-rolled shape guess. See test_mcp_integration.py for the real subprocess round-trip."""
import aixl
from aixl.adapters.protocol_adapter import MCPAdapter, MCPAdapterError


def test_encode_produces_a_real_call_tool_request_params_shape():
    g = aixl.to_semantic("Analiza las ventas de Q1 2026.")
    payload = MCPAdapter().encode(g)
    assert payload["name"] == "aixl_message"
    assert "aixl" in payload["arguments"]
    assert payload["arguments"]["aixl"].startswith("V:AIXL-0.3")


def test_decode_request_shape_round_trips_the_graph():
    g = aixl.to_semantic("Analiza las ventas de Q1 2026.")
    adapter = MCPAdapter()
    g2 = adapter.decode(adapter.encode(g))
    assert g.canonical() == g2.canonical()


def test_decode_call_tool_result_shape_also_round_trips():
    g = aixl.to_semantic("Elimina el reporte.")
    adapter = MCPAdapter()
    aixl_line = adapter.encode(g)["arguments"]["aixl"]
    result_payload = {"content": [{"type": "text", "text": aixl_line}], "isError": False}
    g2 = adapter.decode(result_payload)
    assert g.canonical() == g2.canonical()


def test_decode_rejects_payload_with_no_aixl_anywhere():
    import pytest
    with pytest.raises(MCPAdapterError):
        MCPAdapter().decode({"content": [{"type": "text", "text": None}]})


def test_validate_accepts_well_formed_request_and_result_payloads():
    g = aixl.to_semantic("Analiza las ventas de Q1 2026.")
    req = MCPAdapter().encode(g)
    result = {"content": [{"type": "text", "text": req["arguments"]["aixl"]}], "isError": False}
    assert MCPAdapter().validate(req) == []
    assert MCPAdapter().validate(result) == []


def test_validate_rejects_non_dict_payload():
    errs = MCPAdapter().validate("not a dict")
    assert errs and "dict" in errs[0]


def test_validate_rejects_payload_matching_neither_mcp_shape():
    errs = MCPAdapter().validate({"foo": "bar"})
    assert errs and "neither" in errs[0]


def test_validate_uses_the_real_mcp_sdk_pydantic_models_to_catch_a_malformed_envelope():
    # 'arguments' must be a mapping per the real CallToolRequestParams model — a list is invalid there.
    errs = MCPAdapter().validate({"name": "aixl_message", "arguments": ["not", "a", "mapping"]})
    assert errs and "invalid MCP envelope" in errs[0]


def test_validate_catches_a_well_formed_envelope_carrying_broken_aixl():
    errs = MCPAdapter().validate({"name": "aixl_message", "arguments": {"aixl": "not valid aixl!!"}})
    assert errs and "does not decode" in errs[0]
