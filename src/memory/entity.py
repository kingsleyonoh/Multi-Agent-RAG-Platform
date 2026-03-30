"""Entity memory — extract and track named entities from conversations.

Extracts people, organisations, and dates using regex patterns.
Provides Neo4j integration seams for storage.

Usage::

    from src.memory.entity import EntityMemory, Entity

    em = EntityMemory()
    entities = em.extract_entities("John works at Google.")
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Entity:
    """A single extracted entity."""

    type: str   # "person", "organization", "date"
    value: str


# Pattern → entity type mapping
_ENTITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Organisation names: capitalised multi-word or known companies
    (
        "organization",
        re.compile(
            r"\b(Google|Microsoft|Apple|Amazon|OpenAI|Meta|Netflix|Tesla"
            r"|IBM|Oracle|Intel|Nvidia|Adobe|Salesforce)\b"
        ),
    ),
    # Person names: two or more capitalised words
    (
        "person",
        re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"),
    ),
    # Dates: Month YYYY or YYYY-MM-DD
    (
        "date",
        re.compile(
            r"\b((?:January|February|March|April|May|June|July|August"
            r"|September|October|November|December)\s+\d{4})\b"
            r"|\b(\d{4}-\d{2}-\d{2})\b"
        ),
    ),
]


class EntityMemory:
    """Extract named entities and retrieve conversation context."""

    def __init__(self, *, neo4j_driver=None) -> None:
        self._entities: dict[str, list[Entity]] = {}
        self._neo4j_driver = neo4j_driver

    # ── Testable seams ───────────────────────────────────────────────

    async def _store_entities(self, entities: list[Entity]) -> None:
        """Store entities in Neo4j. No-op when driver is unavailable."""
        if self._neo4j_driver is None:
            return

        async with self._neo4j_driver.session() as session:
            for e in entities:
                await session.run(
                    "MERGE (e:Entity {value: $value}) "
                    "SET e.type = $type",
                    value=e.value,
                    type=e.type,
                )
        logger.debug("entities_stored_neo4j", count=len(entities))

    async def _query_entities(self, entity_values: list[str]) -> list[dict]:
        """Query entities from Neo4j. Returns empty when not wired."""
        if self._neo4j_driver is None:
            return []

        async with self._neo4j_driver.session() as session:
            result = await session.run(
                "MATCH (e:Entity) WHERE e.value IN $values "
                "RETURN e.value AS value, e.type AS type",
                values=entity_values,
            )
            return await result.data()

    # ── Public API ───────────────────────────────────────────────────

    def extract_entities(self, text: str) -> list[Entity]:
        """Extract named entities from text.

        Args:
            text: Input text to scan.

        Returns:
            List of Entity objects found.
        """
        if not text or not text.strip():
            return []

        found: list[Entity] = []
        seen: set[str] = set()

        for entity_type, pattern in _ENTITY_PATTERNS:
            for match in pattern.finditer(text):
                # Groups may return None for alternations
                value = next(
                    (g for g in match.groups() if g is not None),
                    match.group(0),
                )
                if value and value not in seen:
                    seen.add(value)
                    found.append(Entity(type=entity_type, value=value))

        if found:
            logger.debug("entities_extracted", count=len(found))

        return found

    def get_entity_context(self, entities: list[Entity]) -> str:
        """Build context string from entity list.

        Args:
            entities: Entities to include in context.

        Returns:
            Formatted context string.
        """
        if not entities:
            return ""

        lines = [f"- {e.type}: {e.value}" for e in entities]
        return "Known entities:\n" + "\n".join(lines)
