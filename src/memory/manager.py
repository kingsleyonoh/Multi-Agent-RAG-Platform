"""Memory manager — orchestrates all memory subsystems.

Combines short-term, long-term, and entity memory into a unified
context for LLM calls.

Usage::

    from src.memory.manager import MemoryManager

    mm = MemoryManager(window_size=20)
    ctx = await mm.build_context(messages)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from src.memory.entity import EntityMemory
from src.memory.long_term import LongTermMemory
from src.memory.short_term import ShortTermMemory

logger = structlog.get_logger(__name__)


@dataclass
class MemoryContext:
    """Aggregated memory context for LLM calls."""

    context_messages: list[Any] = field(default_factory=list)
    entity_context: str = ""
    memory_summary: str | None = None


class MemoryManager:
    """Orchestrate short-term + long-term + entity memory.

    Args:
        window_size: Messages to keep in short-term window.
        settings: App settings for LLM-backed summarisation.
        neo4j_driver: Neo4j driver for entity storage.
    """

    def __init__(
        self,
        window_size: int = 20,
        *,
        settings=None,
        neo4j_driver=None,
    ) -> None:
        self.short_term = ShortTermMemory(window_size=window_size)
        self.long_term = LongTermMemory(settings=settings)
        self.entity_memory = EntityMemory(neo4j_driver=neo4j_driver)

    async def build_context(self, messages: list[Any]) -> MemoryContext:
        """Build full memory context from conversation messages.

        1. Trim messages to short-term window.
        2. Extract entities from the trimmed messages.
        3. Generate entity context string.
        4. Summarise older messages (async via LLM when wired).

        Args:
            messages: Full conversation history.

        Returns:
            MemoryContext with trimmed messages and entity info.
        """
        # 1. Short-term window
        recent = self.short_term.get_context(messages)

        # 2. Entity extraction from recent messages
        all_entities = []
        for msg in recent:
            content = getattr(msg, "content", str(msg))
            entities = self.entity_memory.extract_entities(content)
            all_entities.extend(entities)

        # 3. Build entity context
        entity_ctx = self.entity_memory.get_entity_context(all_entities)

        # 4. Optional: summarise older messages
        summary = None
        if len(messages) > len(recent):
            older = messages[: len(messages) - len(recent)]
            summary = await self.long_term.summarize(older)

        logger.debug(
            "memory_context_built",
            recent_count=len(recent),
            entity_count=len(all_entities),
            has_summary=summary is not None,
        )

        return MemoryContext(
            context_messages=recent,
            entity_context=entity_ctx,
            memory_summary=summary,
        )
