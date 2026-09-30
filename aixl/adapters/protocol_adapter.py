"""FUTURE-INTEGRATION INTERFACE (spec §37). Nothing here talks to MCP/A2A/REST yet: adapters must be addable
without touching the semantic core. The reference adapters below only prove the interface is implementable."""
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


class _NotImplementedAdapter(ProtocolAdapter):
    def encode(self, graph): raise NotImplementedError(f"{self.name}: planned, not implemented in 0.3")
    def decode(self, payload): raise NotImplementedError(f"{self.name}: planned, not implemented in 0.3")
    def validate(self, payload): raise NotImplementedError(f"{self.name}: planned, not implemented in 0.3")


class MCPAdapter(_NotImplementedAdapter): name = "mcp"
class A2AAdapter(_NotImplementedAdapter): name = "a2a"
class RESTAdapter(_NotImplementedAdapter): name = "rest"
class OpenAPIAdapter(_NotImplementedAdapter): name = "openapi"
class GraphQLAdapter(_NotImplementedAdapter): name = "graphql"
