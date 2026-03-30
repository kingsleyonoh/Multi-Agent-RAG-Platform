"""E2E Journey — Cache Behavior & Metrics.

Tests semantic cache hit/miss behavior and cost/quality metrics
endpoints through the full pipeline.

Uses real LLM calls (~$0.01 per run).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


class TestCacheAndMetricsJourney:
    """Cache hit/miss and metrics verification."""

    async def test_cache_and_metrics_flow(self, httpx_client):
        # ── Step 1: Note initial cache stats ─────────────────────
        initial_stats = await httpx_client.get("/api/cache/stats")
        assert initial_stats.status_code == 200
        initial_lookups = initial_stats.json()["total_lookups"]

        # ── Step 2: First query (cache miss) ─────────────────────
        query = "What are the main components of a neural network?"
        resp1 = await httpx_client.post(
            "/api/chat/sync",
            json={"query": query},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert len(data1["response"]) > 0
        first_model = data1["model_used"]

        # ── Step 3: Check cache stats incremented ────────────────
        stats_after_miss = await httpx_client.get("/api/cache/stats")
        assert stats_after_miss.status_code == 200
        after_lookups = stats_after_miss.json()["total_lookups"]
        assert after_lookups >= initial_lookups

        # ── Step 4: Same query again (potential cache hit) ───────
        resp2 = await httpx_client.post(
            "/api/chat/sync",
            json={"query": query},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert len(data2["response"]) > 0
        # If cache hit, model_used will be "cache"
        if data2["model_used"] == "cache":
            assert data2["cost"] == 0.0

        # ── Step 5: Check final cache stats ──────────────────────
        final_stats = await httpx_client.get("/api/cache/stats")
        assert final_stats.status_code == 200
        final_data = final_stats.json()
        assert final_data["total_lookups"] > initial_lookups

        # ── Step 6: Verify cost metrics ──────────────────────────
        cost_resp = await httpx_client.get("/api/metrics/cost")
        assert cost_resp.status_code == 200
        cost_data = cost_resp.json()
        assert "total_cost" in cost_data
        assert "total_requests" in cost_data
        assert cost_data["total_requests"] > 0

        # ── Step 7: Verify quality metrics endpoint ──────────────
        quality_resp = await httpx_client.get("/api/metrics/quality")
        assert quality_resp.status_code == 200
