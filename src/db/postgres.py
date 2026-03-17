"""Async PostgreSQL connection management with pgvector support.

Provides a cached async engine factory, session factory, pgvector
extension initialisation, and graceful shutdown.  All database modules
import from here — never create engines directly.

Usage::

    from src.db.postgres import get_engine, get_session_factory, init_pgvector

    engine = get_engine(settings.DATABASE_URL)
    await init_pgvector(engine)
    SessionLocal = get_session_factory(engine)
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Module-level engine cache: URL → engine.
# Allows test and app URLs to use separate engines concurrently.
_engines: dict[str, AsyncEngine] = {}


def get_engine(url: str) -> AsyncEngine:
    """Return a cached :class:`AsyncEngine` for *url*.

    On first call for a given *url*, creates a new engine with sensible
    connection pool defaults.  Subsequent calls return the cached instance.
    """
    if url not in _engines:
        _engines[url] = create_async_engine(
            url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
        )
    return _engines[url]


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return an :class:`async_sessionmaker` bound to *engine*.

    Sessions are configured with ``expire_on_commit=False`` so that
    attributes remain accessible after a commit without a refresh.
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def init_pgvector(engine: AsyncEngine) -> None:
    """Ensure the ``vector`` extension is available in the database.

    Safe to call repeatedly — ``CREATE EXTENSION IF NOT EXISTS`` is
    idempotent.
    """
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


async def dispose_engine(engine: AsyncEngine) -> None:
    """Dispose of *engine*, closing all pooled connections.

    Also removes the engine from the module cache so that a fresh
    engine will be created on the next :func:`get_engine` call.
    """
    # Remove from cache first so callers get a fresh engine next time.
    urls_to_remove = [url for url, eng in _engines.items() if eng is engine]
    for url in urls_to_remove:
        del _engines[url]

    await engine.dispose()
