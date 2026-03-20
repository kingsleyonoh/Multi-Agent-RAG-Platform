"""Tests for rate limiting middleware — TDD Red Phase.

The rate limiter must:
- Use Redis INCR+EXPIRE for fixed-window counting per api_key:path:minute
- Return 429 RATE_LIMIT_EXCEEDED when limit exceeded
- Add X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset headers
- Exempt /api/health from rate limiting
- Fail-open when Redis is unreachable
- Apply per-endpoint limits from PRD §8b
- Isolate counters per API key
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.middleware.rate_limit import RateLimitMiddleware


def _make_test_app() -> FastAPI:
    """Create a minimal app with rate limiting for testing."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/documents")
    async def documents():
        return {"documents": []}

    @app.post("/api/search")
    async def search():
        return {"results": []}

    return app


@pytest.fixture
def transport():
    return ASGITransport(app=_make_test_app())


def _mock_redis():
    """Create a mock Redis client with INCR and EXPIRE support."""
    mock = AsyncMock()
    mock.incr = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.ttl = AsyncMock(return_value=60)
    return mock


class TestRateLimitMiddleware:
    """Verify rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_under_limit_returns_200(self, transport):
        """Request under rate limit should succeed."""
        redis_mock = _mock_redis()
        redis_mock.incr.return_value = 1  # first request

        with patch("src.api.middleware.rate_limit._get_redis_client", return_value=redis_mock):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/documents",
                    headers={"X-API-Key": "dev-key-1"},
                )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_over_limit_returns_429(self, transport):
        """Request over rate limit should return 429."""
        redis_mock = _mock_redis()
        redis_mock.incr.return_value = 101  # over 100/min for GET /api/documents

        with patch("src.api.middleware.rate_limit._get_redis_client", return_value=redis_mock):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/documents",
                    headers={"X-API-Key": "dev-key-1"},
                )

        assert response.status_code == 429
        body = response.json()
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, transport):
        """Response must include X-RateLimit-* headers."""
        redis_mock = _mock_redis()
        redis_mock.incr.return_value = 5

        with patch("src.api.middleware.rate_limit._get_redis_client", return_value=redis_mock):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/documents",
                    headers={"X-API-Key": "dev-key-1"},
                )

        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers
        assert "x-ratelimit-reset" in response.headers

    @pytest.mark.asyncio
    async def test_health_endpoint_exempt(self, transport):
        """/api/health must never be rate-limited."""
        redis_mock = _mock_redis()

        with patch("src.api.middleware.rate_limit._get_redis_client", return_value=redis_mock):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/health")

        assert response.status_code == 200
        # Redis should NOT have been called for health
        redis_mock.incr.assert_not_called()

    @pytest.mark.asyncio
    async def test_redis_failure_fails_open(self, transport):
        """Redis errors should allow request through (fail-open)."""
        redis_mock = _mock_redis()
        redis_mock.incr.side_effect = ConnectionError("Redis unavailable")

        with patch("src.api.middleware.rate_limit._get_redis_client", return_value=redis_mock):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/documents",
                    headers={"X-API-Key": "dev-key-1"},
                )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_per_endpoint_limits(self, transport):
        """Different paths should have different rate limits."""
        redis_mock = _mock_redis()
        redis_mock.incr.return_value = 150  # over 100 for docs, under 200 for search

        with patch("src.api.middleware.rate_limit._get_redis_client", return_value=redis_mock):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # /api/documents GET has 100/min → 150 should be blocked
                docs_response = await client.get(
                    "/api/documents",
                    headers={"X-API-Key": "dev-key-1"},
                )
                # /api/search POST has 200/min → 150 should pass
                search_response = await client.post(
                    "/api/search",
                    headers={"X-API-Key": "dev-key-1"},
                )

        assert docs_response.status_code == 429
        assert search_response.status_code == 200

    @pytest.mark.asyncio
    async def test_key_isolation(self, transport):
        """Different API keys should have independent counters."""
        call_count = 0

        async def incr_side_effect(key, *args, **kwargs):
            # Return different counts based on key content
            nonlocal call_count
            call_count += 1
            if "key-alpha" in key:
                return 101  # over limit
            return 1  # under limit

        redis_mock = _mock_redis()
        redis_mock.incr.side_effect = incr_side_effect

        with patch("src.api.middleware.rate_limit._get_redis_client", return_value=redis_mock):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp_alpha = await client.get(
                    "/api/documents",
                    headers={"X-API-Key": "key-alpha"},
                )
                resp_beta = await client.get(
                    "/api/documents",
                    headers={"X-API-Key": "key-beta"},
                )

        assert resp_alpha.status_code == 429
        assert resp_beta.status_code == 200
