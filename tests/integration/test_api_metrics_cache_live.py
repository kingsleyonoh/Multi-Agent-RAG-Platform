"""L3 — Metrics and cache stats API integration tests.

Tests the /api/metrics/cost, /api/metrics/quality, and /api/cache/stats
endpoints against the live server.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


class TestCostMetrics:
    """GET /api/metrics/cost response shape."""

    async def test_cost_metrics_shape(self, httpx_client):
        resp = await httpx_client.get("/api/metrics/cost")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cost" in data
        assert "total_requests" in data
        assert "by_model" in data


class TestQualityMetrics:
    """GET /api/metrics/quality response shape."""

    async def test_quality_metrics_shape(self, httpx_client):
        resp = await httpx_client.get("/api/metrics/quality")
        assert resp.status_code == 200
        data = resp.json()
        # Should have quality metric keys
        assert isinstance(data, dict)


class TestCacheStats:
    """GET /api/cache/stats response shape."""

    async def test_cache_stats_shape(self, httpx_client):
        resp = await httpx_client.get("/api/cache/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_entries" in data
        assert "total_lookups" in data
        assert "total_hits" in data
        assert "hit_rate" in data
        assert "estimated_cost_saved" in data
