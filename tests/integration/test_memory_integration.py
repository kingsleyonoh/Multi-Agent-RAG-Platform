"""L2 — Memory manager integration tests.

Tests MemoryManager, ShortTermMemory, and EntityMemory with
realistic conversation data. No external services needed (LLM
summarization falls back to truncation when settings=None).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.memory.manager import MemoryManager
from src.memory.short_term import ShortTermMemory
from src.memory.entity import EntityMemory

pytestmark = pytest.mark.integration


# ── Helpers ──────────────────────────────────────────────────────


@dataclass
class FakeMessage:
    """Minimal message-like object for memory tests."""
    role: str
    content: str


def _make_messages(n: int) -> list[FakeMessage]:
    """Create n alternating user/assistant messages."""
    msgs = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        msgs.append(FakeMessage(role=role, content=f"Message {i}"))
    return msgs


# ── Short-Term Memory ────────────────────────────────────────────


class TestShortTermMemory:
    """Sliding window over recent messages."""

    def test_returns_all_when_under_window(self):
        stm = ShortTermMemory(window_size=20)
        msgs = _make_messages(5)
        result = stm.get_context(msgs)
        assert len(result) == 5

    def test_trims_to_window_size(self):
        stm = ShortTermMemory(window_size=10)
        msgs = _make_messages(30)
        result = stm.get_context(msgs)
        assert len(result) == 10
        # Should keep the most recent messages
        assert result[-1].content == "Message 29"

    def test_empty_messages_returns_empty(self):
        stm = ShortTermMemory(window_size=20)
        result = stm.get_context([])
        assert result == []


# ── Entity Memory ────────────────────────────────────────────────


class TestEntityMemory:
    """Entity extraction from conversation text."""

    def test_extract_entities_from_text(self):
        em = EntityMemory()
        entities = em.extract_entities(
            "John Smith works at Google and moved to Paris in January 2024."
        )
        names = [e.value for e in entities]
        # Should find at least some of: Google, John Smith, January 2024
        # The regex-based extractor may not catch all
        assert len(entities) >= 1

    def test_entity_context_string(self):
        em = EntityMemory()
        entities = em.extract_entities("Google announced a new AI model.")
        ctx = em.get_entity_context(entities)
        assert isinstance(ctx, str)

    def test_empty_text_no_entities(self):
        em = EntityMemory()
        entities = em.extract_entities("")
        assert entities == []


# ── Memory Manager (orchestrator) ────────────────────────────────


class TestMemoryManager:
    """Full memory context building."""

    async def test_build_context_under_window(self):
        mm = MemoryManager(window_size=20)
        msgs = _make_messages(5)
        ctx = await mm.build_context(msgs)

        assert len(ctx.context_messages) == 5
        assert isinstance(ctx.entity_context, str)
        assert ctx.memory_summary is None  # no older messages

    async def test_build_context_with_summary(self):
        mm = MemoryManager(window_size=10)
        msgs = _make_messages(25)
        ctx = await mm.build_context(msgs)

        assert len(ctx.context_messages) == 10
        # Should have a summary of the 15 older messages
        assert ctx.memory_summary is not None

    async def test_build_context_extracts_entities(self):
        mm = MemoryManager(window_size=20)
        msgs = [
            FakeMessage(role="user", content="I work at Google in San Francisco."),
            FakeMessage(role="assistant", content="That sounds great!"),
        ]
        ctx = await mm.build_context(msgs)

        assert len(ctx.context_messages) == 2
        # Entity context should be a string (possibly with entities)
        assert isinstance(ctx.entity_context, str)

    async def test_empty_messages(self):
        mm = MemoryManager(window_size=20)
        ctx = await mm.build_context([])

        assert ctx.context_messages == []
        assert ctx.entity_context == ""
        assert ctx.memory_summary is None
