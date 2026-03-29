"""Graph API endpoints — entity listing and relationships.

Usage::

    from src.api.routes.graph import router
    app.include_router(router, prefix="/api/graph")
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["graph"])


# ── Neo4j helpers ────────────────────────────────────────────────────

async def _run_cypher(request: Request, query: str, params: dict | None = None) -> list[dict]:
    """Execute a Cypher query against the Neo4j driver on app.state."""
    driver = request.app.state.neo4j_driver
    if driver is None:
        return []
    try:
        async with driver.session() as session:
            result = await session.run(query, params or {})
            records = await result.data()
            return records
    except Exception as exc:
        logger.warning("neo4j_query_error", error=str(exc))
        return []


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/entities")
async def list_entities(
    request: Request,
    limit: int = 50,
    entity_type: str | None = None,
) -> dict:
    """List entities from the knowledge graph.

    Args:
        limit: Maximum entities to return.
        entity_type: Optional filter by entity type.

    Returns:
        Dictionary with entities list.
    """
    if entity_type:
        rows = await _run_cypher(
            request,
            "MATCH (e:Entity {type: $type}) RETURN e.value AS value, e.type AS type LIMIT $limit",
            {"type": entity_type, "limit": limit},
        )
    else:
        rows = await _run_cypher(
            request,
            "MATCH (e:Entity) RETURN e.value AS value, e.type AS type LIMIT $limit",
            {"limit": limit},
        )

    return {"entities": rows, "count": len(rows)}


@router.get("/related/{entity_id}")
async def get_related(request: Request, entity_id: str) -> dict:
    """Get entity and its relationships.

    Args:
        entity_id: Entity value to look up.

    Returns:
        Dictionary with entity info and related entities.
    """
    rows = await _run_cypher(
        request,
        "MATCH (e:Entity {value: $id})-[r]-(related) "
        "RETURN e.value AS entity, type(r) AS rel, related.value AS related_value, related.type AS related_type",
        {"id": entity_id},
    )

    return {
        "entity_id": entity_id,
        "relationships": rows,
        "count": len(rows),
    }
