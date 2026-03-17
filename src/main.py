"""FastAPI application factory with async lifespan management.

Usage::

    # Development
    uvicorn src.main:app --reload

    # Programmatic (tests)
    from src.main import create_app
    app = create_app()
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from src.config import get_settings
from src.db.neo4j import (
    close_driver as close_neo4j,
    get_driver as get_neo4j_driver,
    init_constraints as init_neo4j_constraints,
    verify_connectivity as verify_neo4j,
)
from src.db.postgres import dispose_engine, get_engine, init_pgvector


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown.

    Startup: initialise database pools, caches, etc.
    Shutdown: close connections gracefully.
    """
    settings = get_settings()

    # --- Startup ---
    engine = get_engine(settings.DATABASE_URL)
    await init_pgvector(engine)
    app.state.db_engine = engine

    neo4j_driver = get_neo4j_driver(
        settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD,
    )
    neo4j_ok = await verify_neo4j(neo4j_driver)
    if neo4j_ok:
        await init_neo4j_constraints(neo4j_driver)
    app.state.neo4j_driver = neo4j_driver

    yield

    # --- Shutdown ---
    await close_neo4j(neo4j_driver)
    await dispose_engine(engine)
    # Future: close Redis connection


def create_app() -> FastAPI:
    """Build and return a configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Multi-Agent RAG Platform",
        description=(
            "Production-grade AI backend: RAG, multi-model LLM orchestration, "
            "agents, guardrails, knowledge graph, semantic caching, and MCP server."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # Health endpoint (always available, no auth)
    # ------------------------------------------------------------------
    @app.get("/api/health")
    async def health() -> dict:
        """Liveness / readiness probe."""
        return {
            "status": "ok",
            "environment": settings.ENV,
            "version": app.version,
        }

    return app


# Module-level app instance for `uvicorn src.main:app`
app = create_app()
