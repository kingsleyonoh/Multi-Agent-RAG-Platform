"""Tests for health endpoint — TDD Red Phase.

The health endpoint must:
- Check PostgreSQL connectivity + pgvector extension
- Check Neo4j connectivity
- Check Redis connectivity
- Check LLM provider reachability (OpenRouter)
- Return per-service status with degraded indicators
- Never crash — each check fails independently
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.routes.health import health_router


def _make_test_app():
    """Create a minimal app with the health router and mocked state."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(health_router)

    # Mock app.state attributes that the health router expects
    app.state.db_engine = MagicMock()
    app.state.neo4j_driver = MagicMock()
    app.state.redis_client = MagicMock()

    return app


class TestHealthEndpoint:
    """Verify /api/health per-service connectivity checks."""

    @pytest.mark.asyncio
    async def test_all_services_healthy(self):
        """All services ok → 200, status 'ok'."""
        app = _make_test_app()

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),       # SELECT 1
            MagicMock(scalar=MagicMock(return_value="vector")),  # pgvector
        ])
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        app.state.db_engine.connect = MagicMock(return_value=mock_ctx)

        app.state.neo4j_driver.verify_connectivity = AsyncMock()

        app.state.redis_client.ping = AsyncMock(return_value=True)

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("src.api.routes.health.httpx.AsyncClient") as mock_httpx:
            mock_client_inst = AsyncMock()
            mock_client_inst.get = AsyncMock(return_value=mock_resp)
            mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
            mock_client_inst.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client_inst

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["services"]["postgres"]["status"] == "ok"
        assert body["services"]["neo4j"]["status"] == "ok"
        assert body["services"]["redis"]["status"] == "ok"
        assert body["services"]["llm"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_postgres_down(self):
        """PostgreSQL failure → 200, status 'degraded'."""
        app = _make_test_app()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(side_effect=Exception("pg connection refused"))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        app.state.db_engine.connect = MagicMock(return_value=mock_ctx)

        app.state.neo4j_driver.verify_connectivity = AsyncMock()
        app.state.redis_client.ping = AsyncMock(return_value=True)

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("src.api.routes.health.httpx.AsyncClient") as mock_httpx:
            mock_client_inst = AsyncMock()
            mock_client_inst.get = AsyncMock(return_value=mock_resp)
            mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
            mock_client_inst.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client_inst

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health")

        body = response.json()
        assert body["status"] == "degraded"
        assert body["services"]["postgres"]["status"] == "degraded"
        assert "error" in body["services"]["postgres"]

    @pytest.mark.asyncio
    async def test_neo4j_down(self):
        """Neo4j failure → 200, status 'degraded'."""
        app = _make_test_app()

        # Postgres healthy
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalar=MagicMock(return_value="vector")),
        ])
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        app.state.db_engine.connect = MagicMock(return_value=mock_ctx)

        app.state.neo4j_driver.verify_connectivity = AsyncMock(
            side_effect=Exception("neo4j timeout"),
        )

        app.state.redis_client.ping = AsyncMock(return_value=True)

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("src.api.routes.health.httpx.AsyncClient") as mock_httpx:
            mock_client_inst = AsyncMock()
            mock_client_inst.get = AsyncMock(return_value=mock_resp)
            mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
            mock_client_inst.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client_inst

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health")

        body = response.json()
        assert body["status"] == "degraded"
        assert body["services"]["neo4j"]["status"] == "degraded"
        assert "error" in body["services"]["neo4j"]

    @pytest.mark.asyncio
    async def test_redis_down(self):
        """Redis failure → 200, status 'degraded'."""
        app = _make_test_app()

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalar=MagicMock(return_value="vector")),
        ])
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        app.state.db_engine.connect = MagicMock(return_value=mock_ctx)

        app.state.neo4j_driver.verify_connectivity = AsyncMock()

        app.state.redis_client.ping = AsyncMock(
            side_effect=Exception("redis connection refused"),
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("src.api.routes.health.httpx.AsyncClient") as mock_httpx:
            mock_client_inst = AsyncMock()
            mock_client_inst.get = AsyncMock(return_value=mock_resp)
            mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
            mock_client_inst.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client_inst

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health")

        body = response.json()
        assert body["status"] == "degraded"
        assert body["services"]["redis"]["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_pgvector_missing(self):
        """pgvector not loaded → 200, status 'degraded', postgres warning."""
        app = _make_test_app()

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),       # SELECT 1 ok
            MagicMock(scalar=MagicMock(return_value=None)),    # pgvector missing
        ])
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        app.state.db_engine.connect = MagicMock(return_value=mock_ctx)

        app.state.neo4j_driver.verify_connectivity = AsyncMock()
        app.state.redis_client.ping = AsyncMock(return_value=True)

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("src.api.routes.health.httpx.AsyncClient") as mock_httpx:
            mock_client_inst = AsyncMock()
            mock_client_inst.get = AsyncMock(return_value=mock_resp)
            mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
            mock_client_inst.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client_inst

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health")

        body = response.json()
        assert body["status"] == "degraded"
        assert body["services"]["postgres"]["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_llm_unreachable(self):
        """LLM provider unreachable → 200, status 'degraded'."""
        app = _make_test_app()

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalar=MagicMock(return_value="vector")),
        ])
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        app.state.db_engine.connect = MagicMock(return_value=mock_ctx)

        app.state.neo4j_driver.verify_connectivity = AsyncMock()
        app.state.redis_client.ping = AsyncMock(return_value=True)

        with patch("src.api.routes.health.httpx.AsyncClient") as mock_httpx:
            mock_client_inst = AsyncMock()
            mock_client_inst.get = AsyncMock(side_effect=Exception("timeout"))
            mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
            mock_client_inst.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client_inst

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health")

        body = response.json()
        assert body["status"] == "degraded"
        assert body["services"]["llm"]["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_response_includes_env_and_version(self):
        """Response must include environment and version fields."""
        app = _make_test_app()

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalar=MagicMock(return_value="vector")),
        ])
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        app.state.db_engine.connect = MagicMock(return_value=mock_ctx)

        app.state.neo4j_driver.verify_connectivity = AsyncMock()
        app.state.redis_client.ping = AsyncMock(return_value=True)

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("src.api.routes.health.httpx.AsyncClient") as mock_httpx:
            mock_client_inst = AsyncMock()
            mock_client_inst.get = AsyncMock(return_value=mock_resp)
            mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
            mock_client_inst.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client_inst

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health")

        body = response.json()
        assert "environment" in body
        assert "version" in body

    @pytest.mark.asyncio
    async def test_multiple_services_down(self):
        """Multiple failures → 200, status 'degraded', all affected."""
        app = _make_test_app()

        # Postgres down
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(side_effect=Exception("pg down"))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        app.state.db_engine.connect = MagicMock(return_value=mock_ctx)

        # Neo4j down
        app.state.neo4j_driver.verify_connectivity = AsyncMock(
            side_effect=Exception("neo4j down"),
        )

        # Redis down
        app.state.redis_client.ping = AsyncMock(
            side_effect=Exception("redis down"),
        )

        # LLM down
        with patch("src.api.routes.health.httpx.AsyncClient") as mock_httpx:
            mock_client_inst = AsyncMock()
            mock_client_inst.get = AsyncMock(side_effect=Exception("llm down"))
            mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
            mock_client_inst.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client_inst

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/health")

        body = response.json()
        assert body["status"] == "degraded"
        assert body["services"]["postgres"]["status"] == "degraded"
        assert body["services"]["neo4j"]["status"] == "degraded"
        assert body["services"]["redis"]["status"] == "degraded"
        assert body["services"]["llm"]["status"] == "degraded"
