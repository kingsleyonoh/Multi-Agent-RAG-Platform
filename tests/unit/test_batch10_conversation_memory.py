"""Batch 10 RED tests — Conversation Memory.

Tests for:
- ShortTermMemory (window slicing)
- LongTermMemory (summarization with _call_llm seam)
- EntityMemory (extraction + context)
- MemoryManager (orchestration)
"""

import pytest
from dataclasses import dataclass


# ── Shared test fixtures ─────────────────────────────────────────────

@dataclass
class FakeMessage:
    role: str
    content: str


def _make_messages(n: int) -> list[FakeMessage]:
    return [FakeMessage(role="user", content=f"Message {i}") for i in range(n)]


# ── Short-term memory ────────────────────────────────────────────────

class TestShortTermMemory:
    """Keep last N messages in context window."""

    def test_returns_all_when_under_window(self):
        from src.memory.short_term import ShortTermMemory
        stm = ShortTermMemory(window_size=20)
        messages = _make_messages(5)
        result = stm.get_context(messages)
        assert len(result) == 5

    def test_trims_to_window_size(self):
        from src.memory.short_term import ShortTermMemory
        stm = ShortTermMemory(window_size=5)
        messages = _make_messages(10)
        result = stm.get_context(messages)
        assert len(result) == 5

    def test_keeps_most_recent(self):
        from src.memory.short_term import ShortTermMemory
        stm = ShortTermMemory(window_size=3)
        messages = _make_messages(10)
        result = stm.get_context(messages)
        assert result[-1].content == "Message 9"

    def test_empty_messages(self):
        from src.memory.short_term import ShortTermMemory
        stm = ShortTermMemory(window_size=20)
        result = stm.get_context([])
        assert result == []

    def test_default_window_size(self):
        from src.memory.short_term import ShortTermMemory
        stm = ShortTermMemory()
        assert stm.window_size == 20


# ── Long-term memory ─────────────────────────────────────────────────

class TestLongTermMemory:
    """Summarize older messages for conversation continuity."""

    @pytest.mark.asyncio
    async def test_summarize_produces_text(self):
        from src.memory.long_term import LongTermMemory
        ltm = LongTermMemory()  # no settings → fallback
        messages = _make_messages(5)
        summary = await ltm.summarize(messages)
        assert isinstance(summary, str)
        assert len(summary) > 0

    @pytest.mark.asyncio
    async def test_summarize_empty_messages(self):
        from src.memory.long_term import LongTermMemory
        ltm = LongTermMemory()
        summary = await ltm.summarize([])
        assert summary == ""

    def test_store_and_retrieve_summary(self):
        from src.memory.long_term import LongTermMemory
        ltm = LongTermMemory()
        ltm.store_summary("conv_1", "This was about Python.")
        retrieved = ltm.get_summary("conv_1")
        assert retrieved == "This was about Python."

    def test_missing_summary_returns_none(self):
        from src.memory.long_term import LongTermMemory
        ltm = LongTermMemory()
        assert ltm.get_summary("nonexistent") is None


# ── Entity memory ────────────────────────────────────────────────────

class TestEntityMemory:
    """Extract entities and retrieve context."""

    def test_extract_entities_from_text(self):
        from src.memory.entity import EntityMemory
        em = EntityMemory()
        entities = em.extract_entities(
            "John Smith works at Google since January 2024."
        )
        assert len(entities) > 0

    def test_entity_has_type_and_value(self):
        from src.memory.entity import EntityMemory
        em = EntityMemory()
        entities = em.extract_entities("Microsoft announced new features.")
        # Should have at least one entity with type and value fields
        for entity in entities:
            assert hasattr(entity, "type")
            assert hasattr(entity, "value")

    def test_empty_text_returns_empty(self):
        from src.memory.entity import EntityMemory
        em = EntityMemory()
        entities = em.extract_entities("")
        assert entities == []

    def test_get_entity_context_returns_string(self):
        from src.memory.entity import EntityMemory, Entity
        em = EntityMemory()
        entities = [Entity(type="organization", value="OpenAI")]
        context = em.get_entity_context(entities)
        assert isinstance(context, str)


# ── Memory manager ───────────────────────────────────────────────────

class TestMemoryManager:
    """Orchestrate short-term + long-term + entity memory."""

    @pytest.mark.asyncio
    async def test_build_context_returns_memory_context(self):
        from src.memory.manager import MemoryManager
        mm = MemoryManager()
        messages = _make_messages(5)
        ctx = await mm.build_context(messages)
        assert hasattr(ctx, "context_messages")
        assert hasattr(ctx, "entity_context")

    @pytest.mark.asyncio
    async def test_build_context_trims_messages(self):
        from src.memory.manager import MemoryManager
        mm = MemoryManager(window_size=3)
        messages = _make_messages(10)
        ctx = await mm.build_context(messages)
        assert len(ctx.context_messages) == 3

    @pytest.mark.asyncio
    async def test_build_context_includes_entities(self):
        from src.memory.manager import MemoryManager

        messages = [
            FakeMessage(role="user", content="Tell me about Google's products."),
        ]
        mm = MemoryManager(window_size=20)
        ctx = await mm.build_context(messages)
        assert isinstance(ctx.entity_context, str)
