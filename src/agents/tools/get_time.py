"""Current time tool for agents.

Returns the current UTC timestamp in ISO-8601 format.

Usage::

    from src.agents.tools.get_time import get_time
    timestamp = await get_time()
"""

from __future__ import annotations

from datetime import datetime, timezone


async def get_time() -> str:
    """Return current UTC time as ISO-8601 string.

    Returns:
        UTC timestamp string, e.g. ``"2026-03-21T12:00:00+00:00"``.
    """
    return datetime.now(timezone.utc).isoformat()


# Tool metadata for registry
TOOL_NAME = "get_time"
TOOL_DESCRIPTION = "Get the current UTC time in ISO-8601 format."
TOOL_PARAMETERS = {
    "type": "object",
    "properties": {},
}
