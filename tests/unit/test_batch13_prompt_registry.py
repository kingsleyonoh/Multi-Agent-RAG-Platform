"""Batch 13 — Prompt Registry RED phase tests.

Tests for:
  - PromptRegistry: CRUD, versioning, active flag, model_hint
  - Jinja2 prompt templates
  - Prompt API endpoints (create, list, update)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ── PromptRegistry ────────────────────────────────────────────────────

from src.prompts.registry import PromptRegistry


class TestPromptRegistryCreate:
    """Creating a prompt stores it and returns metadata."""

    def test_create_prompt(self):
        reg = PromptRegistry()
        prompt = reg.create(
            name="rag_system",
            template="You are a helpful assistant. Context: {{ context }}",
            model_hint="openai/gpt-4o",
        )
        assert prompt["name"] == "rag_system"
        assert prompt["version"] == 1
        assert prompt["is_active"] is True

    def test_create_assigns_unique_id(self):
        reg = PromptRegistry()
        p1 = reg.create(name="a", template="t1")
        p2 = reg.create(name="b", template="t2")
        assert p1["id"] != p2["id"]

    def test_create_with_model_hint(self):
        reg = PromptRegistry()
        p = reg.create(name="x", template="t", model_hint="anthropic/claude-3")
        assert p["model_hint"] == "anthropic/claude-3"


class TestPromptRegistryList:
    """List returns all stored prompts."""

    def test_list_empty(self):
        reg = PromptRegistry()
        assert reg.list_all() == []

    def test_list_after_create(self):
        reg = PromptRegistry()
        reg.create(name="a", template="t1")
        reg.create(name="b", template="t2")
        assert len(reg.list_all()) == 2


class TestPromptRegistryGet:
    """Get by ID returns the prompt."""

    def test_get_existing(self):
        reg = PromptRegistry()
        p = reg.create(name="a", template="t")
        found = reg.get(p["id"])
        assert found is not None
        assert found["name"] == "a"

    def test_get_nonexistent_returns_none(self):
        reg = PromptRegistry()
        assert reg.get("nonexistent-id") is None


class TestPromptRegistryUpdate:
    """Updating a prompt increments version and replaces template."""

    def test_update_increments_version(self):
        reg = PromptRegistry()
        p = reg.create(name="a", template="v1")
        updated = reg.update(p["id"], template="v2")
        assert updated["version"] == 2

    def test_update_replaces_template(self):
        reg = PromptRegistry()
        p = reg.create(name="a", template="old")
        updated = reg.update(p["id"], template="new")
        assert updated["template"] == "new"

    def test_update_nonexistent_returns_none(self):
        reg = PromptRegistry()
        assert reg.update("bad-id", template="x") is None


class TestPromptRegistryActiveFlag:
    """The is_active field supports A/B testing."""

    def test_default_is_active(self):
        reg = PromptRegistry()
        p = reg.create(name="a", template="t")
        assert p["is_active"] is True

    def test_deactivate_prompt(self):
        reg = PromptRegistry()
        p = reg.create(name="a", template="t")
        updated = reg.update(p["id"], is_active=False)
        assert updated["is_active"] is False


# ── Jinja2 Template Rendering ────────────────────────────────────────

class TestPromptRegistryRender:
    """Render a Jinja2 template with variables."""

    def test_render_simple(self):
        reg = PromptRegistry()
        p = reg.create(name="sys", template="Hello {{ name }}")
        result = reg.render(p["id"], {"name": "World"})
        assert result == "Hello World"

    def test_render_with_context(self):
        reg = PromptRegistry()
        tmpl = "Context: {{ context }}\nQuestion: {{ question }}"
        p = reg.create(name="rag", template=tmpl)
        result = reg.render(p["id"], {"context": "Python is great", "question": "What?"})
        assert "Python is great" in result
        assert "What?" in result

    def test_render_nonexistent_returns_none(self):
        reg = PromptRegistry()
        assert reg.render("bad-id", {}) is None


# ── Prompt API Endpoints ─────────────────────────────────────────────

from src.api.routes.prompts import router as prompts_router


class TestPromptAPIEndpoints:
    """REST endpoints for prompt CRUD."""

    @pytest.fixture()
    def client(self):
        app = FastAPI()
        app.include_router(prompts_router, prefix="/api/prompts")
        return TestClient(app)

    def test_create_prompt_endpoint(self, client):
        resp = client.post("/api/prompts", json={
            "name": "test",
            "template": "Hello {{ name }}",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "test"

    def test_list_prompts_endpoint(self, client):
        client.post("/api/prompts", json={"name": "a", "template": "t1"})
        resp = client.get("/api/prompts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_update_prompt_endpoint(self, client):
        create_resp = client.post("/api/prompts", json={"name": "a", "template": "v1"})
        pid = create_resp.json()["id"]
        resp = client.put(f"/api/prompts/{pid}", json={"template": "v2"})
        assert resp.status_code == 200
        assert resp.json()["version"] == 2
