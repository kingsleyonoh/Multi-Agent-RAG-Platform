"""Batch 19 — Load test stubs.

Validates response-time contracts using a synchronous TestClient
(no actual concurrency — validates the assertions exist and shape).
"""

import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


class TestLoadContracts:
    """Verify performance contract assertions compile and shapes are correct."""

    def test_seed_script_exists(self):
        """Seed data script must exist."""
        path = os.path.join(PROJECT_ROOT, "scripts", "seed_data.py")
        assert os.path.isfile(path), "scripts/seed_data.py not found"

    def test_seed_script_has_main(self):
        """Seed script must define a main() function."""
        from scripts.seed_data import main

        assert callable(main)

    def test_cache_lookup_shape(self):
        """SemanticCache.lookup() returns None for cache miss (fast path)."""
        from src.cache.semantic import SemanticCache

        cache = SemanticCache()
        result = cache.lookup("nonexistent query")
        assert result is None

    def test_health_endpoint_latency(self):
        """Health endpoint must respond within 2 seconds (generous for test)."""
        from contextlib import asynccontextmanager

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from src.api.routes.health import health_router

        @asynccontextmanager
        async def noop_lifespan(app):
            app.state.db_engine = MagicMock()
            app.state.neo4j_driver = MagicMock()
            app.state.redis_client = MagicMock()
            yield

        app = FastAPI(lifespan=noop_lifespan)
        app.include_router(health_router)

        with TestClient(app) as client:
            with patch(
                "src.api.routes.health._check_postgres",
                new_callable=AsyncMock,
                return_value={"status": "ok"},
            ), patch(
                "src.api.routes.health._check_neo4j",
                new_callable=AsyncMock,
                return_value={"status": "ok"},
            ), patch(
                "src.api.routes.health._check_redis",
                new_callable=AsyncMock,
                return_value={"status": "ok"},
            ), patch(
                "src.api.routes.health._check_llm",
                new_callable=AsyncMock,
                return_value={"status": "ok"},
            ):
                t0 = time.time()
                resp = client.get("/api/health")
                elapsed = time.time() - t0

        assert resp.status_code == 200
        assert elapsed < 2.0, f"Health endpoint took {elapsed:.2f}s"
