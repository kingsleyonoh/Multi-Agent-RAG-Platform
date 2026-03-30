"""L3 — Prompts API integration tests.

Tests prompt CRUD endpoints against the live server.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

_RUN_ID = uuid.uuid4().hex[:8]


class TestPromptCRUD:
    """Prompt create, list, update via API."""

    async def test_create_prompt(self, httpx_client):
        resp = await httpx_client.post(
            "/api/prompts",
            json={
                "name": f"test_prompt_{_RUN_ID}",
                "template": "Hello {{ name }}, welcome!",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["version"] == 1

    async def test_list_prompts_includes_created(self, httpx_client):
        # Create one first
        name = f"test_list_{uuid.uuid4().hex[:8]}"
        await httpx_client.post(
            "/api/prompts",
            json={"name": name, "template": "Test template."},
        )

        resp = await httpx_client.get("/api/prompts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        names = [p["name"] for p in data]
        assert name in names

    async def test_update_prompt_increments_version(self, httpx_client):
        name = f"test_update_{uuid.uuid4().hex[:8]}"
        create_resp = await httpx_client.post(
            "/api/prompts",
            json={"name": name, "template": "Version 1"},
        )
        prompt_id = create_resp.json()["id"]

        update_resp = await httpx_client.put(
            f"/api/prompts/{prompt_id}",
            json={"template": "Version 2"},
        )
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["version"] == 2
