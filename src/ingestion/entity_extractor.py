"""Entity extraction for document ingestion.

Extracts named entities (people, organisations, dates, concepts)
from document chunks and provides a seam for upserting into Neo4j.

Usage::

    from src.ingestion.entity_extractor import extract_entities, upsert_entities

    entities = extract_entities("Google and Microsoft partnered in 2024.")
    upsert_entities(entities, document_id="doc_1")
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

from neo4j import AsyncDriver

logger = structlog.get_logger(__name__)

# Module-level Neo4j driver, wired at startup via init_entity_extractor().
_neo4j_driver: AsyncDriver | None = None


def init_entity_extractor(neo4j_driver: AsyncDriver | None) -> None:
    """Wire the Neo4j driver for entity persistence.

    Called once during application startup from ``main.py``.
    """
    global _neo4j_driver  # noqa: PLW0603
    _neo4j_driver = neo4j_driver
    logger.info("entity_extractor_initialized", has_driver=neo4j_driver is not None)


@dataclass(frozen=True, slots=True)
class ExtractedEntity:
    """An entity extracted during document ingestion."""

    type: str   # "person", "organization", "date", "concept"
    value: str


# ── Extraction patterns ──────────────────────────────────────────────

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "organization",
        re.compile(
            r"\b(Google|Microsoft|Apple|Amazon|OpenAI|Meta|Netflix|Tesla"
            r"|IBM|Oracle|Intel|Nvidia|Adobe|Salesforce|GitHub|Docker)\b"
        ),
    ),
    (
        "person",
        re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"),
    ),
    (
        "date",
        re.compile(
            r"\b((?:January|February|March|April|May|June|July|August"
            r"|September|October|November|December)\s+\d{4})\b"
            r"|\b(\d{4}-\d{2}-\d{2})\b"
        ),
    ),
]


def extract_entities(text: str) -> list[ExtractedEntity]:
    """Extract named entities from a text chunk.

    Args:
        text: Document chunk text.

    Returns:
        List of ExtractedEntity objects.
    """
    if not text or not text.strip():
        return []

    found: list[ExtractedEntity] = []
    seen: set[str] = set()

    for entity_type, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            value = next(
                (g for g in match.groups() if g is not None),
                match.group(0),
            )
            if value and value not in seen:
                seen.add(value)
                found.append(ExtractedEntity(type=entity_type, value=value))

    if found:
        logger.debug("entities_extracted_ingestion", count=len(found))
    return found


# ── Neo4j upsert ─────────────────────────────────────────────────────


async def _run_cypher(query: str, params: dict) -> None:
    """Execute a Cypher statement against the wired Neo4j driver.

    No-ops gracefully when Neo4j is unavailable.
    """
    if _neo4j_driver is None:
        return
    try:
        async with _neo4j_driver.session() as session:
            await session.run(query, params)
    except Exception:
        logger.warning("entity_cypher_failed", exc_info=True)


async def upsert_entities(
    entities: list[ExtractedEntity],
    document_id: str,
) -> None:
    """Upsert extracted entities into Neo4j.

    Creates Entity nodes and EXTRACTED_FROM relationships to the
    source document.  Gracefully no-ops when Neo4j is unavailable.

    Args:
        entities: Entities to store.
        document_id: Source document identifier.
    """
    if not entities or _neo4j_driver is None:
        return

    for entity in entities:
        await _run_cypher(
            "MERGE (e:Entity {value: $value, type: $type}) "
            "MERGE (d:Document {id: $doc_id}) "
            "MERGE (e)-[:EXTRACTED_FROM]->(d)",
            {"value": entity.value, "type": entity.type, "doc_id": document_id},
        )
    logger.info("entities_upserted", count=len(entities), doc=document_id[:12])
