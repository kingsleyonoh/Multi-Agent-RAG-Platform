"""Batch 15 — MCP Server RED phase tests.

Tests for:
  - MCPServer class: initialization, tool registration, tool discovery
  - Tool execution with parameter validation
  - Resource URI scheme support
"""

import pytest

from src.mcp.server import MCPServer


class TestMCPServerInit:
    """MCPServer can be instantiated with port and transport."""

    def test_default_port(self):
        server = MCPServer()
        assert server.port == 3001

    def test_custom_port(self):
        server = MCPServer(port=4000)
        assert server.port == 4000

    def test_default_transport(self):
        server = MCPServer()
        assert server.transport == "stdio"

    def test_custom_transport(self):
        server = MCPServer(transport="sse")
        assert server.transport == "sse"


class TestMCPToolRegistration:
    """Tools can be registered and listed."""

    def test_register_tool(self):
        server = MCPServer()
        server.register_tool(
            name="search_documents",
            description="Search the knowledge base.",
            parameters={"query": {"type": "string", "required": True}},
            handler=lambda params: {"results": []},
        )
        tools = server.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "search_documents"

    def test_register_multiple_tools(self):
        server = MCPServer()
        for name in ["search_documents", "ingest_document", "query_graph"]:
            server.register_tool(
                name=name,
                description=f"{name} tool",
                parameters={},
                handler=lambda params: {},
            )
        assert len(server.list_tools()) == 3


class TestMCPToolDiscovery:
    """Tool discovery returns name, description, and parameter schema."""

    def test_tool_has_name(self):
        server = MCPServer()
        server.register_tool("t", "desc", {}, lambda p: {})
        tool = server.list_tools()[0]
        assert "name" in tool

    def test_tool_has_description(self):
        server = MCPServer()
        server.register_tool("t", "desc", {}, lambda p: {})
        tool = server.list_tools()[0]
        assert tool["description"] == "desc"

    def test_tool_has_parameters(self):
        server = MCPServer()
        params = {"query": {"type": "string"}}
        server.register_tool("t", "desc", params, lambda p: {})
        tool = server.list_tools()[0]
        assert tool["parameters"] == params


class TestMCPToolExecution:
    """Executing a tool calls the registered handler."""

    def test_execute_returns_result(self):
        server = MCPServer()
        server.register_tool(
            "echo",
            "Echo tool",
            {"message": {"type": "string"}},
            lambda params: {"echo": params.get("message", "")},
        )
        result = server.execute_tool("echo", {"message": "hello"})
        assert result == {"echo": "hello"}

    def test_execute_nonexistent_raises(self):
        server = MCPServer()
        with pytest.raises(KeyError):
            server.execute_tool("nonexistent", {})


class TestMCPResourceSchemes:
    """Resources with URI schemes can be registered."""

    def test_register_resource(self):
        server = MCPServer()
        server.register_resource(
            uri_scheme="document://",
            description="Document resources",
            handler=lambda uri: {"content": ""},
        )
        resources = server.list_resources()
        assert len(resources) == 1
        assert resources[0]["uri_scheme"] == "document://"

    def test_read_resource(self):
        server = MCPServer()
        server.register_resource(
            "document://",
            "docs",
            lambda uri: {"content": f"doc:{uri}"},
        )
        result = server.read_resource("document://test-id")
        assert result["content"] == "doc:document://test-id"
