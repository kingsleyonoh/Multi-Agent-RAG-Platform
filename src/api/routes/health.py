"""Health endpoint with per-service connectivity checks.

Probes PostgreSQL (+ pgvector), Neo4j, Redis, and the LLM provider.
Each check fails independently — a single failure degrades status but
never crashes the endpoint.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Request
from sqlalchemy import text

from src.config import get_settings

health_router = APIRouter(prefix="/api", tags=["health"])


# ── Individual probes ──────────────────────────────────────────────


async def _check_postgres(engine: Any) -> dict[str, str]:
    """SELECT 1 + verify pgvector extension is loaded."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            row = await conn.execute(
                text(
                    "SELECT extname FROM pg_extension WHERE extname = 'vector'"
                )
            )
            ext = row.scalar()
            if ext is None:
                return {
                    "status": "degraded",
                    "error": "pgvector extension not installed",
                }
            return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "error": str(exc)}


async def _check_neo4j(driver: Any) -> dict[str, str]:
    """Verify Neo4j driver connectivity."""
    try:
        await driver.verify_connectivity()
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "error": str(exc)}


async def _check_redis(client: Any) -> dict[str, str]:
    """PING the Redis server."""
    try:
        await client.ping()
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "error": str(exc)}


async def _check_llm() -> dict[str, str]:
    """Lightweight reachability check against OpenRouter."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.OPENROUTER_BASE_URL}/models",
                headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
            )
            if resp.status_code == 200:
                return {"status": "ok"}
            return {
                "status": "degraded",
                "error": f"LLM API returned {resp.status_code}",
            }
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "error": str(exc)}


# ── Route ──────────────────────────────────────────────────────────


@health_router.get("/health")
async def health_check(request: Request) -> dict[str, Any]:
    """Comprehensive health check with per-service status."""
    settings = get_settings()

    postgres = await _check_postgres(request.app.state.db_engine)
    neo4j = await _check_neo4j(request.app.state.neo4j_driver)
    redis = await _check_redis(request.app.state.redis_client)
    llm = await _check_llm()

    services = {
        "postgres": postgres,
        "neo4j": neo4j,
        "redis": redis,
        "llm": llm,
    }

    overall = (
        "ok"
        if all(s["status"] == "ok" for s in services.values())
        else "degraded"
    )

    return {
        "status": overall,
        "environment": settings.ENV,
        "version": "0.1.0",
        "services": services,
    }
