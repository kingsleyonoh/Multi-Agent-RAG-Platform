"""FastAPI application factory with async lifespan management.

Usage::

    # Development
    uvicorn src.main:app --reload

    # Programmatic (tests)
    from src.main import create_app
    app = create_app()
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI

from src.api.middleware.errors import register_error_handlers
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.middleware.request_id import RequestIDMiddleware
from src.api.routes.cache import router as cache_router
from src.api.routes.chat import router as chat_router
from src.api.routes.conversations import router as conversations_router
from src.api.routes.documents import router as documents_router
from src.api.routes.graph import router as graph_router
from src.api.routes.health import health_router
from src.api.routes.metrics import router as metrics_router
from src.api.routes.prompts import router as prompts_router
from src.api.routes.search import router as search_router
from src.agents.tools.query_graph import init_query_graph
from src.agents.tools.search_kb import init_search_kb
from src.agents.tools.summarize import init_summarize
from src.ingestion.entity_extractor import init_entity_extractor
from src.cache.semantic import SemanticCache as SemanticCacheService
from src.config import get_settings
from src.db.models import Base
from src.db.neo4j import (
    close_driver as close_neo4j,
    get_driver as get_neo4j_driver,
    init_constraints as init_neo4j_constraints,
    verify_connectivity as verify_neo4j,
)
from src.db.postgres import dispose_engine, get_engine, get_session_factory, init_pgvector
from src.db.redis import close_client as close_redis, get_client as get_redis_client
from src.llm.cost_tracker import CostTracker
from src.retrieval.graph_search import init_graph_search

logger = structlog.get_logger(__name__)

# Seconds to wait for each resource to close before giving up.
_SHUTDOWN_TIMEOUT: float = 5.0

# Set when the application is shutting down.  Other modules can
# ``await get_shutdown_event().wait()`` or check ``.is_set()``.
_shutdown_event = asyncio.Event()


def get_shutdown_event() -> asyncio.Event:
    """Return the module-level shutdown event."""
    return _shutdown_event


async def _dispose_resource(
    name: str,
    coro,
    *args,
    timeout: float | None = None,
) -> None:
    """Close a single resource with timeout and error isolation.

    Parameters
    ----------
    name:
        Human-readable label for log messages (e.g. ``"Redis"``).
    coro:
        Async callable (the close/dispose function).
    *args:
        Positional arguments forwarded to *coro*.
    timeout:
        Max seconds to wait.  Falls back to ``_SHUTDOWN_TIMEOUT``.
    """
    effective_timeout = timeout if timeout is not None else _SHUTDOWN_TIMEOUT
    try:
        await asyncio.wait_for(coro(*args), timeout=effective_timeout)
        logger.info("resource_closed", resource=name)
    except asyncio.TimeoutError:
        logger.warning(
            "resource_close_timeout",
            resource=name,
            timeout_s=effective_timeout,
        )
    except Exception:
        logger.warning("resource_close_error", resource=name, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown.

    Startup: initialise database pools, caches, etc.
    Shutdown: signal the event, then dispose resources in order
    (Redis → Neo4j → PostgreSQL) with timeout + error isolation.
    """
    settings = get_settings()

    # --- Startup ---
    engine = get_engine(settings.DATABASE_URL)
    await init_pgvector(engine)
    app.state.db_engine = engine
    logger.info("startup_resource_ready", resource="PostgreSQL")

    # Create all tables (idempotent — safe to call every startup)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("startup_tables_created")

    neo4j_driver = get_neo4j_driver(
        settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD,
    )
    neo4j_ok = await verify_neo4j(neo4j_driver)
    if neo4j_ok:
        await init_neo4j_constraints(neo4j_driver)
    app.state.neo4j_driver = neo4j_driver
    logger.info("startup_resource_ready", resource="Neo4j", connected=neo4j_ok)

    redis_client = get_redis_client(settings.REDIS_URL)
    app.state.redis_client = redis_client
    logger.info("startup_resource_ready", resource="Redis")

    # Shared service instances
    app.state.cost_tracker = CostTracker()
    app.state.semantic_cache = SemanticCacheService(
        similarity_threshold=settings.CACHE_SIMILARITY_THRESHOLD,
        ttl_hours=settings.CACHE_TTL_HOURS,
        settings=settings,
    )
    app.state.settings = settings
    logger.info("startup_services_ready")

    # Wire agent tools and ingestion to live infrastructure
    init_search_kb(get_session_factory(engine), settings)
    init_query_graph(neo4j_driver)
    init_summarize(settings)
    init_graph_search(neo4j_driver)
    init_entity_extractor(neo4j_driver)
    logger.info("startup_tools_initialized")

    yield

    # --- Shutdown ---
    t0 = time.monotonic()
    logger.info("shutdown_started")
    _shutdown_event.set()

    # Dispose in spec order: Redis → Neo4j → PostgreSQL
    await _dispose_resource("Redis", close_redis, redis_client)
    await _dispose_resource("Neo4j", close_neo4j, neo4j_driver)
    await _dispose_resource("PostgreSQL", dispose_engine, engine)

    elapsed = time.monotonic() - t0
    logger.info("shutdown_complete", elapsed_s=round(elapsed, 3))


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

    # --- Middleware (outermost first) ---
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # --- Exception handlers ---
    register_error_handlers(app, env=settings.ENV)

    # --- Routes ---
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(search_router)
    app.include_router(chat_router)
    app.include_router(conversations_router)
    app.include_router(graph_router, prefix="/api/graph")
    app.include_router(prompts_router, prefix="/api/prompts")
    app.include_router(metrics_router, prefix="/api/metrics")
    app.include_router(cache_router, prefix="/api/cache")

    return app


# Module-level app instance for `uvicorn src.main:app`
app = create_app()
