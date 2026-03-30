"""L3 — Conversations API integration tests.

Tests the full conversation lifecycle (create, list, get, add message,
delete) against the live server with real PostgreSQL.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


class TestConversationLifecycle:
    """Full CRUD lifecycle for conversations."""

    @pytest.fixture
    async def conversation(self, httpx_client):
        """Create a conversation and delete after test."""
        resp = await httpx_client.post(
            "/api/conversations",
            json={"user_id": "e2e-test-user", "title": f"Test {uuid.uuid4().hex[:8]}"},
        )
        data = resp.json()
        yield data
        await httpx_client.delete(f"/api/conversations/{data['id']}")

    async def test_create_conversation(self, httpx_client):
        resp = await httpx_client.post(
            "/api/conversations",
            json={"user_id": "e2e-test-user", "title": "Create Test"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["user_id"] == "e2e-test-user"
        assert data["title"] == "Create Test"
        # Cleanup
        await httpx_client.delete(f"/api/conversations/{data['id']}")

    async def test_list_conversations(self, httpx_client, conversation):
        resp = await httpx_client.get(
            "/api/conversations",
            params={"user_id": "e2e-test-user"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        conv_ids = [c["id"] for c in data]
        assert conversation["id"] in conv_ids

    async def test_get_conversation_with_messages(self, httpx_client, conversation):
        resp = await httpx_client.get(f"/api/conversations/{conversation['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == conversation["id"]
        assert "messages" in data
        assert isinstance(data["messages"], list)

    async def test_add_message_to_conversation(self, httpx_client, conversation):
        resp = await httpx_client.post(
            f"/api/conversations/{conversation['id']}/messages",
            json={"role": "user", "content": "Hello from integration test!"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["role"] == "user"
        assert data["content"] == "Hello from integration test!"

    async def test_messages_appear_in_get(self, httpx_client, conversation):
        # Add a message first
        await httpx_client.post(
            f"/api/conversations/{conversation['id']}/messages",
            json={"role": "user", "content": "Test message"},
        )

        # Verify it appears
        resp = await httpx_client.get(f"/api/conversations/{conversation['id']}")
        data = resp.json()
        assert len(data["messages"]) >= 1
        contents = [m["content"] for m in data["messages"]]
        assert "Test message" in contents

    async def test_delete_conversation(self, httpx_client):
        # Create then delete
        create_resp = await httpx_client.post(
            "/api/conversations",
            json={"user_id": "e2e-test-user", "title": "Delete Me"},
        )
        conv_id = create_resp.json()["id"]

        del_resp = await httpx_client.delete(f"/api/conversations/{conv_id}")
        assert del_resp.status_code == 204

    async def test_get_deleted_conversation_404(self, httpx_client):
        create_resp = await httpx_client.post(
            "/api/conversations",
            json={"user_id": "e2e-test-user", "title": "Will Delete"},
        )
        conv_id = create_resp.json()["id"]
        await httpx_client.delete(f"/api/conversations/{conv_id}")

        resp = await httpx_client.get(f"/api/conversations/{conv_id}")
        assert resp.status_code == 404

    async def test_delete_nonexistent_conversation_404(self, httpx_client):
        fake_id = str(uuid.uuid4())
        resp = await httpx_client.delete(f"/api/conversations/{fake_id}")
        assert resp.status_code == 404
