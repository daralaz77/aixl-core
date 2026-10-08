"""FUTURE-INTEGRATION INTERFACE (spec §37). Nothing here talks to REST/OpenAPI/GraphQL yet: adapters must
be addable without touching the semantic core. MCPAdapter (2026-09-30, E-MCP) was the first REAL one: it
validates against the actual pydantic models of the official `mcp` SDK (package `mcp`, MCP spec 2025-06-18),
not a hand-rolled guess of the wire shape. See aixl/mcp_server.py for a real running server and
tests/test_mcp_integration.py for a real stdio subprocess round-trip proving this is not just shape-matching.
A2AAdapter (2026-09-30, E-A2A) is the second REAL one, over Google's official `a2a-sdk`: see
aixl/agents/a2a_server.py for a real running HTTP agent and tests/test_a2a_integration.py for a real
subprocess + real client round-trip over actual JSON-RPC/HTTP."""
from abc import ABC, abstractmethod

from aixl.core.semantic_graph import SemanticGraph
from aixl.serialization import aixl_codec, json_codec


class ProtocolAdapter(ABC):
    name = "abstract"

    @abstractmethod
    def encode(self, graph: SemanticGraph):            # graph -> protocol payload
        ...

    @abstractmethod
    def decode(self, payload) -> SemanticGraph:         # protocol payload -> graph
        ...

    @abstractmethod
    def validate(self, payload) -> list:                # list of error strings (empty = valid)
        ...


class AixlAdapter(ProtocolAdapter):
    name = "aixl"

    def encode(self, graph): return aixl_codec.encode(graph)
    def decode(self, payload): return aixl_codec.decode(payload)

    def validate(self, payload):
        try:
            aixl_codec.decode(payload); return []
        except aixl_codec.AixlError as e:
            return [str(e)]


class JsonAdapter(ProtocolAdapter):
    name = "json"

    def encode(self, graph): return json_codec.dumps(graph)
    def decode(self, payload): return json_codec.loads(payload)

    def validate(self, payload):
        try:
            json_codec.loads(payload); return []
        except Exception as e:                           # noqa: BLE001
            return [f"invalid semantic-graph JSON: {type(e).__name__}"]


class MCPAdapterError(Exception):
    pass


class MCPAdapter(ProtocolAdapter):
    """Carries an AIXL message inside a REAL MCP tool-call envelope (package `mcp`, the official Python SDK).

    Two real MCP shapes, both supported because a full exchange needs both directions:
      - a CallToolRequestParams: {"name": "aixl_message", "arguments": {"aixl": "<AIXL line>"}}
        (one agent asking another, over MCP, to act on this semantic graph)
      - a CallToolResult: {"content": [{"type": "text", "text": "<AIXL line>"}], "isError": false}
        (the answer coming back)
    `validate()` runs the payload through the SDK's OWN pydantic models (mcp.types), so a malformed envelope is
    caught by the real spec's rules, not by rules this project invented — this is what makes it a REAL adapter
    rather than a plausible-looking mock."""
    name = "mcp"
    TOOL_NAME = "aixl_message"

    def encode(self, graph: SemanticGraph) -> dict:
        aixl_line = aixl_codec.encode(graph)
        return {"name": self.TOOL_NAME, "arguments": {"aixl": aixl_line}}

    def decode(self, payload: dict) -> SemanticGraph:
        aixl_line = self._extract_aixl(payload)
        if aixl_line is None:
            raise MCPAdapterError("payload is neither a CallToolRequestParams with arguments.aixl "
                                   "nor a CallToolResult with a text content item")
        return aixl_codec.decode(aixl_line)

    def validate(self, payload) -> list:
        import mcp.types as t
        errors = []
        if not isinstance(payload, dict):
            return [f"payload must be a dict, got {type(payload).__name__}"]
        is_request = "arguments" in payload or "name" in payload
        is_result = "content" in payload
        if not is_request and not is_result:
            return ["payload matches neither CallToolRequestParams nor CallToolResult shape"]
        try:
            if is_request:
                t.CallToolRequestParams.model_validate(payload)
            else:
                t.CallToolResult.model_validate(payload)
        except Exception as e:                            # noqa: BLE001 — real pydantic ValidationError
            errors.append(f"invalid MCP envelope ({type(e).__name__}): {e}")
            return errors
        aixl_line = self._extract_aixl(payload)
        if aixl_line is None:
            errors.append("MCP envelope is well-formed but carries no 'aixl' argument / text content")
            return errors
        try:
            aixl_codec.decode(aixl_line)
        except aixl_codec.AixlError as e:
            errors.append(f"embedded AIXL does not decode: {e}")
        return errors

    @staticmethod
    def _extract_aixl(payload: dict) -> str | None:
        if not isinstance(payload, dict):
            return None
        args = payload.get("arguments")
        if isinstance(args, dict) and isinstance(args.get("aixl"), str):
            return args["aixl"]
        for item in payload.get("content") or []:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                return item["text"]
        return None


class A2AAdapterError(Exception):
    pass


class A2AAdapter(ProtocolAdapter):
    """Carries an AIXL message inside a REAL A2A Message envelope (package `a2a-sdk`, Google's official
    Agent2Agent Python SDK). The AIXL line travels as a text Part — exactly what this project's own real
    running agent (aixl/agents/a2a_server.py) and the official SDK's own client actually exchange over
    JSON-RPC/HTTP, proven end-to-end by tests/test_a2a_integration.py's real subprocess round-trip, not
    just here.
    `validate()` runs the payload through the SDK's OWN protobuf message (a2a.types.a2a_pb2.Message) via
    google.protobuf.json_format.ParseDict — the real spec's own parser, not a hand-rolled shape check —
    same "REAL adapter, not a plausible-looking mock" standard as MCPAdapter."""
    name = "a2a"

    def encode(self, graph: SemanticGraph) -> dict:
        from a2a.helpers.proto_helpers import new_text_message
        from google.protobuf.json_format import MessageToDict
        aixl_line = aixl_codec.encode(graph)
        return MessageToDict(new_text_message(aixl_line))

    def decode(self, payload: dict) -> SemanticGraph:
        aixl_line = self._extract_aixl(payload)
        if aixl_line is None:
            raise A2AAdapterError("payload is not an A2A Message with a text Part carrying an AIXL line")
        return aixl_codec.decode(aixl_line)

    def validate(self, payload) -> list:
        from a2a.types.a2a_pb2 import Message
        from google.protobuf.json_format import ParseDict, ParseError
        if not isinstance(payload, dict):
            return [f"payload must be a dict, got {type(payload).__name__}"]
        try:
            ParseDict(payload, Message())
        except ParseError as e:
            return [f"invalid A2A Message envelope ({type(e).__name__}): {e}"]
        aixl_line = self._extract_aixl(payload)
        if aixl_line is None:
            return ["A2A Message is well-formed but carries no text Part"]
        try:
            aixl_codec.decode(aixl_line)
        except aixl_codec.AixlError as e:
            return [f"embedded AIXL does not decode: {e}"]
        return []

    @staticmethod
    def _extract_aixl(payload) -> str | None:
        if not isinstance(payload, dict):
            return None
        for part in payload.get("parts") or []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                return part["text"]
        return None


class _NotImplementedAdapter(ProtocolAdapter):
    def encode(self, graph): raise NotImplementedError(f"{self.name}: planned, not implemented in 0.3")
    def decode(self, payload): raise NotImplementedError(f"{self.name}: planned, not implemented in 0.3")
    def validate(self, payload): raise NotImplementedError(f"{self.name}: planned, not implemented in 0.3")


class RESTAdapter(_NotImplementedAdapter): name = "rest"
class OpenAPIAdapter(_NotImplementedAdapter): name = "openapi"
class GraphQLAdapter(_NotImplementedAdapter): name = "graphql"
