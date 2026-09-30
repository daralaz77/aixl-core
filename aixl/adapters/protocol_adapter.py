"""FUTURE-INTEGRATION INTERFACE (spec §37). Nothing here talks to A2A/REST/OpenAPI/GraphQL yet: adapters must
be addable without touching the semantic core. MCPAdapter (2026-09-30, E-MCP) is the first REAL one: it validates
against the actual pydantic models of the official `mcp` SDK (package `mcp`, MCP spec 2025-06-18), not a hand-rolled
guess of the wire shape. See aixl/mcp_server.py for a real running server and tests/test_mcp_integration.py for a
real stdio subprocess round-trip proving this is not just shape-matching."""
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


class _NotImplementedAdapter(ProtocolAdapter):
    def encode(self, graph): raise NotImplementedError(f"{self.name}: planned, not implemented in 0.3")
    def decode(self, payload): raise NotImplementedError(f"{self.name}: planned, not implemented in 0.3")
    def validate(self, payload): raise NotImplementedError(f"{self.name}: planned, not implemented in 0.3")


class A2AAdapter(_NotImplementedAdapter): name = "a2a"
class RESTAdapter(_NotImplementedAdapter): name = "rest"
class OpenAPIAdapter(_NotImplementedAdapter): name = "openapi"
class GraphQLAdapter(_NotImplementedAdapter): name = "graphql"
