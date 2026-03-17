"""Integration tests for src/db/postgres — requires a running PostgreSQL instance.

These tests exercise real database connections via the Docker Compose
PostgreSQL service (port 5433 with pgvector image).
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.db.postgres import (
    _engines,
    dispose_engine,
    get_engine,
    get_session_factory,
    init_pgvector,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _clear_engine_cache():
    """Clear the module-level engine cache before each test.

    This prevents shared-engine interference between tests.
    """
    _engines.clear()
    yield
    _engines.clear()


class TestInitPgvector:
    """Tests for init_pgvector()."""

    async def test_init_pgvector_creates_extension(self, database_url: str) -> None:
        """init_pgvector() ensures the 'vector' extension exists."""
        engine = get_engine(database_url)
        try:
            await init_pgvector(engine)

            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        "SELECT extname FROM pg_extension WHERE extname = 'vector'"
                    )
                )
                row = result.scalar_one_or_none()
                assert row == "vector"
        finally:
            await engine.dispose()


class TestSessionFactory:
    """Tests for session factory with a real database."""

    async def test_session_can_execute_query(self, database_url: str) -> None:
        """A session from the factory can execute a simple query."""
        engine = get_engine(database_url)
        try:
            factory = get_session_factory(engine)

            async with factory() as session:
                async with session.begin():
                    result = await session.execute(text("SELECT 1 AS val"))
                    assert result.scalar_one() == 1
        finally:
            await engine.dispose()


class TestDisposeEngine:
    """Tests for dispose_engine()."""

    async def test_dispose_engine_removes_from_cache(
        self, database_url: str
    ) -> None:
        """After disposal the engine is removed from the module cache."""
        engine = get_engine(database_url)

        # Engine is in the cache before disposal.
        assert database_url in _engines

        await dispose_engine(engine)

        # Cache entry removed after disposal.
        assert database_url not in _engines

        # A new engine for the same URL is a fresh instance.
        new_engine = get_engine(database_url)
        assert new_engine is not engine

        async with new_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar_one() == 1

        await new_engine.dispose()
