"""Tests for src/main.py — FastAPI app factory and health endpoint.

RED phase: these tests should fail until src/main.py is implemented.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


class TestCreateApp:
    """Verify that create_app returns a properly configured FastAPI app."""

    def test_returns_fastapi_instance(self):
        from fastapi import FastAPI

        app = create_app()
        assert isinstance(app, FastAPI)

    def test_app_title_is_set(self):
        app = create_app()
        assert app.title == "Multi-Agent RAG Platform"


class TestHealthEndpoint:
    """The /api/health endpoint must return status ok."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self):
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_returns_status_ok(self):
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_returns_environment(self):
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")
        data = response.json()
        assert "environment" in data
