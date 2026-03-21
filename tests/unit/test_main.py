"""Tests for src/main.py — FastAPI app factory and health endpoint wiring.

The detailed health-check coverage lives in ``test_health.py``.
These tests verify the endpoint is properly wired into the app.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


def _stub_app_state(app):
    """Attach mock service objects so the health router can run."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(side_effect=[
        MagicMock(scalar=MagicMock(return_value=1)),
        MagicMock(scalar=MagicMock(return_value="vector")),
    ])
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    app.state.db_engine = MagicMock()
    app.state.db_engine.connect = MagicMock(return_value=mock_ctx)
    app.state.neo4j_driver = MagicMock()
    app.state.neo4j_driver.verify_connectivity = AsyncMock()
    app.state.redis_client = MagicMock()
    app.state.redis_client.ping = AsyncMock(return_value=True)


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
    """The /api/health endpoint must be wired and return expected shape."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self):
        app = create_app()
        _stub_app_state(app)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("src.api.routes.health.httpx.AsyncClient") as mock_httpx:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = inst
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_returns_status_ok(self):
        app = create_app()
        _stub_app_state(app)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("src.api.routes.health.httpx.AsyncClient") as mock_httpx:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = inst
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health")
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_returns_environment(self):
        app = create_app()
        _stub_app_state(app)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("src.api.routes.health.httpx.AsyncClient") as mock_httpx:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = inst
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health")
        data = response.json()
        assert "environment" in data
