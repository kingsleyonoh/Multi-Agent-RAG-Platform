"""Batch 19 — Integration Tests (e2e via TestClient).

Tests all API endpoints using FastAPI TestClient with mocked
infrastructure (DB, LLM, etc.) to verify routing, status codes,
and response shapes.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """Create a TestClient with mocked lifespan and app state."""
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    from src.api.routes.chat import router as chat_router
    from src.api.routes.conversations import router as conversations_router
    from src.api.routes.documents import router as documents_router
    from src.api.routes.health import health_router
    from src.api.routes.search import router as search_router

    @asynccontextmanager
    async def noop_lifespan(app):
        # Provide fake state objects so health endpoint can use them
        app.state.db_engine = MagicMock()
        app.state.neo4j_driver = MagicMock()
        app.state.redis_client = MagicMock()
        yield

    app = FastAPI(lifespan=noop_lifespan)
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(search_router)
    app.include_router(chat_router)
    app.include_router(conversations_router)

    with TestClient(app) as c:
        yield c


# ── Health ───────────────────────────────────────────────────────────


class TestHealthE2E:
    """Health endpoint integration tests."""

    def test_health_returns_200(self, client):
        """GET /api/health returns 200."""
        with patch(
            "src.api.routes.health._check_postgres",
            new_callable=AsyncMock,
            return_value={"status": "ok"},
        ), patch(
            "src.api.routes.health._check_neo4j",
            new_callable=AsyncMock,
            return_value={"status": "ok"},
        ), patch(
            "src.api.routes.health._check_redis",
            new_callable=AsyncMock,
            return_value={"status": "ok"},
        ), patch(
            "src.api.routes.health._check_llm",
            new_callable=AsyncMock,
            return_value={"status": "ok"},
        ):
            resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_returns_json(self, client):
        """Health response must be JSON with 'status' key."""
        with patch(
            "src.api.routes.health._check_postgres",
            new_callable=AsyncMock,
            return_value={"status": "ok"},
        ), patch(
            "src.api.routes.health._check_neo4j",
            new_callable=AsyncMock,
            return_value={"status": "ok"},
        ), patch(
            "src.api.routes.health._check_redis",
            new_callable=AsyncMock,
            return_value={"status": "ok"},
        ), patch(
            "src.api.routes.health._check_llm",
            new_callable=AsyncMock,
            return_value={"status": "ok"},
        ):
            resp = client.get("/api/health")
        data = resp.json()
        assert "status" in data
        assert data["status"] == "ok"


# ── Documents ────────────────────────────────────────────────────────


class TestDocumentsE2E:
    """Document ingestion endpoint integration tests."""

    def test_upload_no_file_returns_422(self, client):
        """POST /api/documents with no file returns 422."""
        resp = client.post("/api/documents")
        assert resp.status_code == 422

    def test_url_ingest_missing_url_returns_422(self, client):
        """POST /api/documents/url with no url field returns 422."""
        resp = client.post("/api/documents/url", json={})
        assert resp.status_code == 422


# ── Search ───────────────────────────────────────────────────────────


class TestSearchE2E:
    """Search endpoint integration tests."""

    def test_search_missing_query_returns_422(self, client):
        """POST /api/search with no query returns 422."""
        resp = client.post("/api/search", json={})
        assert resp.status_code == 422


# ── Chat ─────────────────────────────────────────────────────────────


class TestChatE2E:
    """Chat endpoint integration tests."""

    def test_chat_missing_message_returns_422(self, client):
        """POST /api/chat with no message returns 422."""
        resp = client.post("/api/chat", json={})
        assert resp.status_code == 422
