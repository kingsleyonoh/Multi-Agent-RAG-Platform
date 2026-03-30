"""FastAPI dependency injection factories.

Provides request-scoped dependencies for database sessions, settings,
Neo4j driver, and shared services (cost tracker, semantic cache).

Usage::

    from src.api.dependencies import get_db_session, get_settings_dep

    @router.post("/example")
    async def example(
        session: AsyncSession = Depends(get_db_session),
        settings: Settings = Depends(get_settings_dep),
    ):
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.db.postgres import get_session_factory


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional DB session from the app's engine.

    The session is created per-request and closed automatically
    when the request ends.
    """
    engine = request.app.state.db_engine
    factory = get_session_factory(engine)
    async with factory() as session:
        yield session


def get_settings_dep() -> Settings:
    """Return the cached application settings singleton."""
    return get_settings()


def get_neo4j_driver(request: Request):
    """Return the Neo4j driver from app state."""
    return request.app.state.neo4j_driver


def get_cost_tracker(request: Request):
    """Return the shared CostTracker from app state."""
    return request.app.state.cost_tracker


def get_semantic_cache(request: Request):
    """Return the shared SemanticCache from app state."""
    return request.app.state.semantic_cache
