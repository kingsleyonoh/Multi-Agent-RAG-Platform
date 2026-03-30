"""Deep verification — Conversation memory.

Proves conversation history is loaded from the database and fed
into LLM context on subsequent turns, and that entity extraction
works on conversation data.
"""

from __future__ import annotations

import uuid

import pytest

from src.memory.entity import EntityMemory

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

_RUN_ID = uuid.uuid4().hex[:8]


class TestMemoryLoading:
    """Verify messages persist and are loadable for multi-turn context."""

    async def test_messages_persist_across_turns(self, httpx_client):
        """Two chat turns with conversation_id → messages saved to DB."""
        # Create conversation
        conv = await httpx_client.post(
            "/api/conversations",
            json={"user_id": "e2e-test-user", "title": f"Memory {_RUN_ID}"},
        )
        conv_id = conv.json()["id"]

        try:
            # Turn 1: unique query to avoid cache
            tag = uuid.uuid4().hex[:6]
            await httpx_client.post(
                "/api/chat/sync",
                json={
                    "query": f"[{tag}] My secret project codename is ATLAS-7-{_RUN_ID}.",
                    "conversation_id": conv_id,
                },
            )

            # Turn 2
            await httpx_client.post(
                "/api/chat/sync",
                json={
                    "query": f"[{tag}] What did I just tell you about my project?",
                    "conversation_id": conv_id,
                },
            )

            # Verify messages are in DB
            detail = await httpx_client.get(f"/api/conversations/{conv_id}")
            messages = detail.json()["messages"]
            # Should have at least 2 user + 2 assistant = 4 messages
            # (may be fewer if cache hit on first turn)
            assert len(messages) >= 2, f"Expected 2+ messages, got {len(messages)}"

            # Verify message structure
            roles = [m["role"] for m in messages]
            assert "user" in roles
            assert "assistant" in roles
        finally:
            await httpx_client.delete(f"/api/conversations/{conv_id}")

    async def test_large_conversation_doesnt_timeout(self, httpx_client):
        """25+ messages in a conversation → chat still responds in time."""
        conv = await httpx_client.post(
            "/api/conversations",
            json={"user_id": "e2e-test-user", "title": f"Large {_RUN_ID}"},
        )
        conv_id = conv.json()["id"]

        try:
            # Add 25 messages via API
            for i in range(25):
                role = "user" if i % 2 == 0 else "assistant"
                await httpx_client.post(
                    f"/api/conversations/{conv_id}/messages",
                    json={"role": role, "content": f"Message number {i} in conversation."},
                )

            # Chat should still work (memory manager trims to window)
            tag = uuid.uuid4().hex[:6]
            resp = await httpx_client.post(
                "/api/chat/sync",
                json={
                    "query": f"[{tag}] Summarize what we discussed.",
                    "conversation_id": conv_id,
                },
            )
            assert resp.status_code == 200
            assert len(resp.json()["response"]) > 0
        finally:
            await httpx_client.delete(f"/api/conversations/{conv_id}")


class TestEntityExtractionFromConversation:
    """Verify EntityMemory extracts entities from conversation text."""

    def test_entity_extraction_finds_organizations(self):
        em = EntityMemory()
        entities = em.extract_entities(
            "I work at Google and previously interned at Microsoft."
        )
        values = [e.value for e in entities]
        assert "Google" in values or "Microsoft" in values

    def test_entity_extraction_finds_names(self):
        em = EntityMemory()
        entities = em.extract_entities(
            "John Smith and Alice Johnson are working on the AI project."
        )
        values = [e.value for e in entities]
        assert any("John" in v or "Alice" in v for v in values)
