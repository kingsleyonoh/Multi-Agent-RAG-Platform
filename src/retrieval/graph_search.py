"""Graph search — query Neo4j for entity-related context.

Uses a Cypher seam for testability without a live Neo4j instance.

Usage::

    from src.retrieval.graph_search import search_graph

    results = await search_graph(query_entities=["Google", "AI"])
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class GraphResult:
    """A graph search result with entity and related chunks."""

    entity: str
    related_chunks: list[str] = field(default_factory=list)


# ── Module-level state (set by init_graph_search at startup) ─────

_neo4j_driver = None


def init_graph_search(neo4j_driver) -> None:
    """Wire graph search to a live Neo4j driver.

    Called once at app startup from ``main.py`` lifespan.
    """
    global _neo4j_driver
    _neo4j_driver = neo4j_driver
    logger.info("graph_search_initialized")


async def _run_cypher(query: str, params: dict) -> list[dict]:
    """Execute a Cypher query against Neo4j.

    Gracefully returns empty list when Neo4j is not wired or
    unavailable (connection errors, DNS resolution failures).
    """
    if _neo4j_driver is None:
        return []

    try:
        async with _neo4j_driver.session() as session:
            result = await session.run(query, **params)
            return await result.data()
    except Exception:
        logger.warning("graph_search_cypher_failed", exc_info=True)
        return []


async def search_graph(query_entities: list[str]) -> list[GraphResult]:
    """Search the knowledge graph for entities.

    Queries Neo4j for entities matching the query terms and
    returns connected document chunks.

    Args:
        query_entities: Entity names to search for.

    Returns:
        List of GraphResult with entity and related chunks.
    """
    if not query_entities:
        return []

    results: list[GraphResult] = []

    for entity_name in query_entities:
        rows = await _run_cypher(
            "MATCH (e:Entity {value: $name})-[:EXTRACTED_FROM]->(d:Document) "
            "RETURN e.value AS entity, d.id AS chunk_id",
            {"name": entity_name},
        )
        if rows:
            chunks = [r.get("chunk_id", "") for r in rows]
            results.append(GraphResult(entity=entity_name, related_chunks=chunks))

    if results:
        logger.debug("graph_search_results", count=len(results))

    return results
