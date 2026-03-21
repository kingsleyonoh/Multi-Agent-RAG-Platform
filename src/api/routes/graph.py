"""Graph API endpoints — entity listing and relationships.

Usage::

    from src.api.routes.graph import router
    app.include_router(router, prefix="/api/graph")
"""

from __future__ import annotations

from fastapi import APIRouter

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["graph"])


# ── Testable seams ───────────────────────────────────────────────────

def _run_cypher(query: str, params: dict | None = None) -> list[dict]:
    """Seam for Neo4j Cypher execution. Override in tests."""
    return []


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/entities")
async def list_entities(
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
        rows = _run_cypher(
            "MATCH (e:Entity {type: $type}) RETURN e LIMIT $limit",
            {"type": entity_type, "limit": limit},
        )
    else:
        rows = _run_cypher(
            "MATCH (e:Entity) RETURN e LIMIT $limit",
            {"limit": limit},
        )

    return {"entities": rows, "count": len(rows)}


@router.get("/related/{entity_id}")
async def get_related(entity_id: str) -> dict:
    """Get entity and its relationships.

    Args:
        entity_id: Entity value to look up.

    Returns:
        Dictionary with entity info and related entities.
    """
    rows = _run_cypher(
        "MATCH (e:Entity {value: $id})-[r]-(related) "
        "RETURN e, type(r) AS rel, related",
        {"id": entity_id},
    )

    return {
        "entity_id": entity_id,
        "relationships": rows,
        "count": len(rows),
    }
