"""L3 — Authentication and rate limiting API integration tests.

Tests auth middleware (API key validation) and rate limit headers
against the live running server.
"""

from __future__ import annotations

import httpx
import pytest

from tests.conftest import LIVE_SERVER_URL

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


class TestAuthentication:
    """API key validation against the live server."""

    async def test_missing_api_key_returns_401(self):
        async with httpx.AsyncClient(base_url=LIVE_SERVER_URL, timeout=10) as client:
            resp = await client.get("/api/documents")
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["code"] == "MISSING_API_KEY"

    async def test_invalid_api_key_returns_403(self):
        async with httpx.AsyncClient(
            base_url=LIVE_SERVER_URL,
            headers={"X-API-Key": "totally-invalid-key"},
            timeout=10,
        ) as client:
            resp = await client.get("/api/documents")
        assert resp.status_code == 403
        data = resp.json()
        assert data["error"]["code"] == "INVALID_API_KEY"

    async def test_valid_api_key_passes(self, httpx_client):
        resp = await httpx_client.get("/api/documents")
        assert resp.status_code == 200


class TestRateLimiting:
    """Rate limit headers on authenticated requests."""

    async def test_rate_limit_headers_present(self, httpx_client):
        resp = await httpx_client.get("/api/documents")
        assert "x-ratelimit-limit" in resp.headers
        assert "x-ratelimit-remaining" in resp.headers
        assert "x-ratelimit-reset" in resp.headers

    async def test_rate_limit_remaining_decrements(self, httpx_client):
        resp1 = await httpx_client.get("/api/documents")
        remaining1 = int(resp1.headers["x-ratelimit-remaining"])

        resp2 = await httpx_client.get("/api/documents")
        remaining2 = int(resp2.headers["x-ratelimit-remaining"])

        assert remaining2 <= remaining1


class TestErrorFormat:
    """PRD-compliant error response format."""

    async def test_validation_error_format(self, httpx_client):
        resp = await httpx_client.post("/api/search", json={})
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
