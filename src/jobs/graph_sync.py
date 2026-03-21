"""Knowledge graph sync job.

Extracts entities from document content and upserts them into the
graph store (Neo4j).  Designed to be triggered as a FastAPI
``BackgroundTasks`` callback after document ingestion.

Usage::

    from src.jobs.graph_sync import sync_graph

    count = sync_graph(
        content=doc_text,
        entity_extractor=extractor,
        graph_store=store,
    )
"""

from __future__ import annotations

from typing import Any, Protocol


class EntityExtractor(Protocol):
    """Protocol for entity extractors."""

    def extract(self, text: str) -> list[dict[str, Any]]: ...


class GraphStore(Protocol):
    """Protocol for graph store backends."""

    def upsert_entities(self, entities: list[dict[str, Any]]) -> None: ...


def sync_graph(
    *,
    content: str,
    entity_extractor: EntityExtractor,
    graph_store: GraphStore,
) -> int:
    """Extract entities from *content* and upsert into *graph_store*.

    Returns the number of entities upserted.
    """
    entities = entity_extractor.extract(content)
    if not entities:
        return 0
    graph_store.upsert_entities(entities)
    return len(entities)
