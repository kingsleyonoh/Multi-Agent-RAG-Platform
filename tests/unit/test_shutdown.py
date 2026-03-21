"""Tests for graceful shutdown behaviour in src/main.py lifespan.

Verifies:
- Shutdown event is set when lifespan exits
- Resources are disposed in correct order (Redis → Neo4j → PostgreSQL)
- One resource failure doesn't prevent closing subsequent resources
- Hung resources are timed out
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from src.main import create_app, get_shutdown_event


def _make_startup_mocks():
    """Return a dict of patches that stub out all startup I/O."""
    engine = MagicMock()
    neo4j_driver = MagicMock()
    redis_client = MagicMock()

    return {
        "engine": engine,
        "neo4j_driver": neo4j_driver,
        "redis_client": redis_client,
        "patches": {
            "get_engine": patch("src.main.get_engine", return_value=engine),
            "init_pgvector": patch("src.main.init_pgvector", new_callable=AsyncMock),
            "get_neo4j_driver": patch("src.main.get_neo4j_driver", return_value=neo4j_driver),
            "verify_neo4j": patch("src.main.verify_neo4j", new_callable=AsyncMock, return_value=True),
            "init_neo4j_constraints": patch("src.main.init_neo4j_constraints", new_callable=AsyncMock),
            "get_redis_client": patch("src.main.get_redis_client", return_value=redis_client),
            "close_redis": patch("src.main.close_redis", new_callable=AsyncMock),
            "close_neo4j": patch("src.main.close_neo4j", new_callable=AsyncMock),
            "dispose_engine": patch("src.main.dispose_engine", new_callable=AsyncMock),
        },
    }


async def _run_lifespan(app):
    """Run the full lifespan (startup + shutdown) for *app*."""
    ctx = app.router.lifespan_context(app)
    await ctx.__aenter__()
    await ctx.__aexit__(None, None, None)


class TestShutdownEvent:
    """The shutdown event must be set once lifespan exits."""

    @pytest.mark.asyncio
    async def test_shutdown_event_is_set_after_lifespan_exits(self):
        app = create_app()
        mocks = _make_startup_mocks()
        with (
            mocks["patches"]["get_engine"],
            mocks["patches"]["init_pgvector"],
            mocks["patches"]["get_neo4j_driver"],
            mocks["patches"]["verify_neo4j"],
            mocks["patches"]["init_neo4j_constraints"],
            mocks["patches"]["get_redis_client"],
            mocks["patches"]["close_redis"],
            mocks["patches"]["close_neo4j"],
            mocks["patches"]["dispose_engine"],
        ):
            await _run_lifespan(app)

        assert get_shutdown_event().is_set()


class TestShutdownOrder:
    """Resources must be disposed in order: Redis → Neo4j → PostgreSQL."""

    @pytest.mark.asyncio
    async def test_shutdown_closes_redis_before_neo4j(self):
        app = create_app()
        mocks = _make_startup_mocks()
        call_order: list[str] = []

        async def track_redis(*a, **kw):
            call_order.append("redis")

        async def track_neo4j(*a, **kw):
            call_order.append("neo4j")

        async def track_pg(*a, **kw):
            call_order.append("postgres")

        with (
            mocks["patches"]["get_engine"],
            mocks["patches"]["init_pgvector"],
            mocks["patches"]["get_neo4j_driver"],
            mocks["patches"]["verify_neo4j"],
            mocks["patches"]["init_neo4j_constraints"],
            mocks["patches"]["get_redis_client"],
            patch("src.main.close_redis", side_effect=track_redis),
            patch("src.main.close_neo4j", side_effect=track_neo4j),
            patch("src.main.dispose_engine", side_effect=track_pg),
        ):
            await _run_lifespan(app)

        assert call_order.index("redis") < call_order.index("neo4j")

    @pytest.mark.asyncio
    async def test_shutdown_closes_neo4j_before_postgres(self):
        app = create_app()
        mocks = _make_startup_mocks()
        call_order: list[str] = []

        async def track_redis(*a, **kw):
            call_order.append("redis")

        async def track_neo4j(*a, **kw):
            call_order.append("neo4j")

        async def track_pg(*a, **kw):
            call_order.append("postgres")

        with (
            mocks["patches"]["get_engine"],
            mocks["patches"]["init_pgvector"],
            mocks["patches"]["get_neo4j_driver"],
            mocks["patches"]["verify_neo4j"],
            mocks["patches"]["init_neo4j_constraints"],
            mocks["patches"]["get_redis_client"],
            patch("src.main.close_redis", side_effect=track_redis),
            patch("src.main.close_neo4j", side_effect=track_neo4j),
            patch("src.main.dispose_engine", side_effect=track_pg),
        ):
            await _run_lifespan(app)

        assert call_order.index("neo4j") < call_order.index("postgres")

    @pytest.mark.asyncio
    async def test_shutdown_closes_postgres_last(self):
        app = create_app()
        mocks = _make_startup_mocks()
        call_order: list[str] = []

        async def track_redis(*a, **kw):
            call_order.append("redis")

        async def track_neo4j(*a, **kw):
            call_order.append("neo4j")

        async def track_pg(*a, **kw):
            call_order.append("postgres")

        with (
            mocks["patches"]["get_engine"],
            mocks["patches"]["init_pgvector"],
            mocks["patches"]["get_neo4j_driver"],
            mocks["patches"]["verify_neo4j"],
            mocks["patches"]["init_neo4j_constraints"],
            mocks["patches"]["get_redis_client"],
            patch("src.main.close_redis", side_effect=track_redis),
            patch("src.main.close_neo4j", side_effect=track_neo4j),
            patch("src.main.dispose_engine", side_effect=track_pg),
        ):
            await _run_lifespan(app)

        assert call_order[-1] == "postgres"


class TestShutdownErrorIsolation:
    """One resource failing to close must NOT prevent others from closing."""

    @pytest.mark.asyncio
    async def test_shutdown_continues_on_redis_error(self):
        app = create_app()
        mocks = _make_startup_mocks()

        mock_close_neo4j = AsyncMock()
        mock_dispose_engine = AsyncMock()

        with (
            mocks["patches"]["get_engine"],
            mocks["patches"]["init_pgvector"],
            mocks["patches"]["get_neo4j_driver"],
            mocks["patches"]["verify_neo4j"],
            mocks["patches"]["init_neo4j_constraints"],
            mocks["patches"]["get_redis_client"],
            patch("src.main.close_redis", side_effect=RuntimeError("Redis gone")),
            patch("src.main.close_neo4j", mock_close_neo4j),
            patch("src.main.dispose_engine", mock_dispose_engine),
        ):
            await _run_lifespan(app)

        mock_close_neo4j.assert_awaited_once()
        mock_dispose_engine.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_continues_on_neo4j_error(self):
        app = create_app()
        mocks = _make_startup_mocks()

        mock_dispose_engine = AsyncMock()

        with (
            mocks["patches"]["get_engine"],
            mocks["patches"]["init_pgvector"],
            mocks["patches"]["get_neo4j_driver"],
            mocks["patches"]["verify_neo4j"],
            mocks["patches"]["init_neo4j_constraints"],
            mocks["patches"]["get_redis_client"],
            mocks["patches"]["close_redis"],
            patch("src.main.close_neo4j", side_effect=RuntimeError("Neo4j gone")),
            patch("src.main.dispose_engine", mock_dispose_engine),
        ):
            await _run_lifespan(app)

        mock_dispose_engine.assert_awaited_once()


class TestShutdownTimeout:
    """Resources that hang beyond timeout must not block shutdown."""

    @pytest.mark.asyncio
    async def test_shutdown_timeout_protects_hung_resource(self):
        app = create_app()
        mocks = _make_startup_mocks()

        async def hang_forever(*a, **kw):
            await asyncio.sleep(999)

        mock_close_neo4j = AsyncMock()
        mock_dispose_engine = AsyncMock()

        with (
            mocks["patches"]["get_engine"],
            mocks["patches"]["init_pgvector"],
            mocks["patches"]["get_neo4j_driver"],
            mocks["patches"]["verify_neo4j"],
            mocks["patches"]["init_neo4j_constraints"],
            mocks["patches"]["get_redis_client"],
            patch("src.main.close_redis", side_effect=hang_forever),
            patch("src.main.close_neo4j", mock_close_neo4j),
            patch("src.main.dispose_engine", mock_dispose_engine),
            patch("src.main._SHUTDOWN_TIMEOUT", 0.1),
        ):
            await _run_lifespan(app)

        # Despite Redis hanging, Neo4j and Postgres were still cleaned up
        mock_close_neo4j.assert_awaited_once()
        mock_dispose_engine.assert_awaited_once()
