"""MCP (Model Context Protocol) server implementation.

Provides tool registration, discovery, execution, and resource URI
scheme support.  In production the server listens on ``MCP_SERVER_PORT``
(default 3001) using ``MCP_TRANSPORT`` (default ``stdio``).

Compatible with MCP-aware clients (Claude Desktop, Cursor, etc.).
"""

from __future__ import annotations

from typing import Any, Callable


class MCPServer:
    """Lightweight MCP server with tool and resource registries.

    Parameters
    ----------
    port:
        Network port for non-stdio transports (default 3001).
    transport:
        Transport type: ``stdio`` or ``sse`` (default ``stdio``).
    """

    def __init__(
        self,
        *,
        port: int = 3001,
        transport: str = "stdio",
    ) -> None:
        self.port = port
        self.transport = transport
        self._tools: dict[str, dict[str, Any]] = {}
        self._resources: dict[str, dict[str, Any]] = {}

    # ── tools ────────────────────────────────────────────────────────

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Register a callable tool."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler,
        }

    def list_tools(self) -> list[dict[str, Any]]:
        """Return all registered tools (without handlers)."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            }
            for t in self._tools.values()
        ]

    def execute_tool(
        self,
        name: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a registered tool by name, raising *KeyError* if missing."""
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]["handler"](params)

    # ── resources ────────────────────────────────────────────────────

    def register_resource(
        self,
        uri_scheme: str,
        description: str,
        handler: Callable[[str], dict[str, Any]],
    ) -> None:
        """Register a URI resource scheme."""
        self._resources[uri_scheme] = {
            "uri_scheme": uri_scheme,
            "description": description,
            "handler": handler,
        }

    def list_resources(self) -> list[dict[str, Any]]:
        """Return all registered resource schemes (without handlers)."""
        return [
            {
                "uri_scheme": r["uri_scheme"],
                "description": r["description"],
            }
            for r in self._resources.values()
        ]

    def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource by URI, matching the scheme prefix."""
        for scheme, resource in self._resources.items():
            if uri.startswith(scheme):
                return resource["handler"](uri)
        raise KeyError(f"No handler for URI: {uri}")
