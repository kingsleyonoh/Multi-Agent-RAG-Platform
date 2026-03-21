"""Agent tool registry.

Provides a typed registry for agent tools with whitelist enforcement.

Usage::

    from src.agents.registry import ToolRegistry, ToolSpec

    registry = ToolRegistry()
    registry.register(ToolSpec(name="search", ...))
    tool = registry.get("search")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import structlog

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class ToolSpec:
    """Specification for an agent tool.

    Attributes:
        name: Unique tool identifier.
        description: Human-readable description for the LLM.
        parameters: JSON Schema describing tool parameters.
        handler: Async callable that executes the tool.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]


class ToolRegistry:
    """Registry of available agent tools with whitelist enforcement.

    Only registered tools can be invoked by the agent executor.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        """Register a tool. Overwrites if name already exists.

        Args:
            spec: Tool specification to register.
        """
        self._tools[spec.name] = spec
        logger.debug("tool_registered", name=spec.name)

    def get(self, name: str) -> ToolSpec | None:
        """Get a tool by name.

        Args:
            name: Tool identifier.

        Returns:
            ToolSpec if found, None otherwise.
        """
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """Return all registered tool names.

        Returns:
            List of tool name strings.
        """
        return list(self._tools.keys())

    def is_whitelisted(self, name: str) -> bool:
        """Check if a tool name is registered (whitelisted).

        Args:
            name: Tool identifier.

        Returns:
            True if tool is registered.
        """
        return name in self._tools

    def to_openai_tools(self) -> list[dict]:
        """Export tools in OpenAI function-calling format.

        Returns:
            List of tool definitions for the ``tools`` API parameter.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            }
            for spec in self._tools.values()
        ]
