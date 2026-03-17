"""Unit tests for src/db/postgres — async engine, session factory, pgvector init.

These tests verify the public API of the postgres module without requiring
a running database (engine creation and caching are tested in-memory).
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.db.postgres import (
    dispose_engine,
    get_engine,
    get_session_factory,
    init_pgvector,
)


class TestGetEngine:
    """Tests for get_engine() factory function."""

    def test_get_engine_returns_async_engine(self) -> None:
        """get_engine() returns an AsyncEngine instance."""
        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        engine = get_engine(url)
        assert isinstance(engine, AsyncEngine)

    def test_get_engine_caches_by_url(self) -> None:
        """Same URL returns the exact same engine object (cached)."""
        url = "postgresql+asyncpg://user:pass@localhost:5432/cachetest"
        engine_a = get_engine(url)
        engine_b = get_engine(url)
        assert engine_a is engine_b

    def test_get_engine_different_urls_different_engines(self) -> None:
        """Different URLs produce distinct engine instances."""
        url_1 = "postgresql+asyncpg://user:pass@localhost:5432/db_one"
        url_2 = "postgresql+asyncpg://user:pass@localhost:5432/db_two"
        engine_1 = get_engine(url_1)
        engine_2 = get_engine(url_2)
        assert engine_1 is not engine_2


class TestGetSessionFactory:
    """Tests for get_session_factory()."""

    def test_returns_async_sessionmaker(self) -> None:
        """get_session_factory() returns an async_sessionmaker instance."""
        url = "postgresql+asyncpg://user:pass@localhost:5432/session_test"
        engine = get_engine(url)
        factory = get_session_factory(engine)
        assert isinstance(factory, async_sessionmaker)

    def test_expire_on_commit_is_false(self) -> None:
        """Session factory is configured with expire_on_commit=False."""
        url = "postgresql+asyncpg://user:pass@localhost:5432/expire_test"
        engine = get_engine(url)
        factory = get_session_factory(engine)
        # async_sessionmaker stores kw in .kw dict
        assert factory.kw.get("expire_on_commit") is False
