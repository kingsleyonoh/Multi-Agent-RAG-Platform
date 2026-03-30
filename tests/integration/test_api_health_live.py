"""L3 — Health endpoint API integration tests.

Tests the /api/health endpoint against the live running server
with real infrastructure checks.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


class TestHealthEndpoint:
    """Verify health endpoint with all real services."""

    async def test_health_returns_200(self, httpx_client):
        resp = await httpx_client.get("/api/health")
        assert resp.status_code == 200

    async def test_health_response_shape(self, httpx_client):
        resp = await httpx_client.get("/api/health")
        data = resp.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "services" in data
        for svc in ("postgres", "neo4j", "redis", "llm"):
            assert svc in data["services"]
            assert data["services"][svc]["status"] == "ok"

    async def test_health_has_environment(self, httpx_client):
        resp = await httpx_client.get("/api/health")
        data = resp.json()
        assert "environment" in data
        assert "version" in data

    async def test_request_id_header_present(self, httpx_client):
        resp = await httpx_client.get("/api/health")
        assert "x-request-id" in resp.headers

    async def test_custom_request_id_echoed(self, httpx_client):
        custom_id = "test-request-id-12345"
        resp = await httpx_client.get(
            "/api/health",
            headers={"X-Request-ID": custom_id},
        )
        assert resp.headers.get("x-request-id") == custom_id
