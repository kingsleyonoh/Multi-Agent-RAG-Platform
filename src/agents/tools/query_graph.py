"""Neo4j graph query tool for agents.

Executes read-only Cypher queries against the knowledge graph.

Usage::

    from src.agents.tools.query_graph import query_graph
    results = await query_graph(cypher="MATCH (n:Entity) RETURN n.name LIMIT 5")
"""

from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Patterns that indicate write operations
_WRITE_PATTERNS = re.compile(
    r"\b(CREATE|DELETE|DETACH\s+DELETE|SET|MERGE|REMOVE)\b",
    re.IGNORECASE,
)

# ── Module-level state (set by init_query_graph at startup) ──────

_neo4j_driver = None


def init_query_graph(neo4j_driver) -> None:
    """Wire query_graph to a live Neo4j driver.

    Called once at app startup from ``main.py`` lifespan.
    """
    global _neo4j_driver
    _neo4j_driver = neo4j_driver
    logger.info("query_graph_initialized")


async def _execute_cypher(cypher: str) -> list[dict[str, Any]]:
    """Execute a Cypher query against the live Neo4j instance.

    Gracefully returns empty list when Neo4j is not wired.
    """
    if _neo4j_driver is None:
        logger.debug("query_graph_not_wired")
        return []

    async with _neo4j_driver.session() as session:
        result = await session.run(cypher)
        records = await result.data()
        return records


async def query_graph(*, cypher: str) -> list[dict[str, Any]]:
    """Execute a read-only Cypher query against the knowledge graph.

    Args:
        cypher: Cypher query string. Must be read-only.

    Returns:
        List of record dicts from the query result.

    Raises:
        ValueError: If the query contains write operations.
    """
    if _WRITE_PATTERNS.search(cypher):
        raise ValueError(
            f"Only read-only Cypher queries are allowed. "
            f"Detected write operation in: {cypher[:100]}"
        )

    logger.info("query_graph_called", cypher_len=len(cypher))
    return await _execute_cypher(cypher)


# Tool metadata for registry
TOOL_NAME = "query_graph"
TOOL_DESCRIPTION = "Execute a read-only Cypher query against the knowledge graph."
TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "cypher": {
            "type": "string",
            "description": "Read-only Cypher query string",
        },
    },
    "required": ["cypher"],
}
