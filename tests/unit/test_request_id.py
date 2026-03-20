"""Tests for Request ID middleware — TDD Red Phase.

The middleware must:
- Generate UUID4 per request and return it in X-Request-ID header
- Bind request_id to structlog contextvars for log correlation
- Clear structlog context after response (no leaking between requests)
- Honour client-provided X-Request-ID if non-empty
"""

import uuid

import pytest
import structlog
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.fixture
def app():
    """Create a fresh FastAPI app with middleware registered."""
    return create_app()


@pytest.fixture
def transport(app):
    return ASGITransport(app=app)


class TestRequestIDMiddleware:
    """Verify X-Request-ID generation, propagation, and structlog binding."""

    @pytest.mark.asyncio
    async def test_response_has_request_id_header(self, transport):
        """Every response must include an X-Request-ID header."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")

        assert response.status_code == 200
        assert "x-request-id" in response.headers

    @pytest.mark.asyncio
    async def test_request_id_is_valid_uuid4(self, transport):
        """The generated request ID must be a valid UUID4."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")

        request_id = response.headers["x-request-id"]
        parsed = uuid.UUID(request_id, version=4)
        assert str(parsed) == request_id

    @pytest.mark.asyncio
    async def test_unique_ids_per_request(self, transport):
        """Each request must get a different request ID."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r1 = await client.get("/api/health")
            r2 = await client.get("/api/health")

        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]

    @pytest.mark.asyncio
    async def test_honours_client_provided_id(self, transport):
        """If client sends X-Request-ID, use it instead of generating one."""
        custom_id = "client-trace-abc-123"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/health",
                headers={"X-Request-ID": custom_id},
            )

        assert response.headers["x-request-id"] == custom_id

    @pytest.mark.asyncio
    async def test_empty_client_id_generates_new(self, transport):
        """Empty X-Request-ID header should be ignored — generate a new UUID."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/health",
                headers={"X-Request-ID": ""},
            )

        request_id = response.headers["x-request-id"]
        # Must be a valid UUID, not empty
        assert request_id != ""
        uuid.UUID(request_id, version=4)

    @pytest.mark.asyncio
    async def test_whitespace_client_id_generates_new(self, transport):
        """Whitespace-only X-Request-ID should be treated as absent."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/health",
                headers={"X-Request-ID": "   "},
            )

        request_id = response.headers["x-request-id"]
        assert request_id.strip() != ""
        uuid.UUID(request_id, version=4)

    @pytest.mark.asyncio
    async def test_structlog_context_cleared_after_request(self, transport):
        """After request completes, structlog contextvars must be empty."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/api/health")

        # After the request, bound context should NOT contain request_id
        ctx = structlog.contextvars.get_contextvars()
        assert "request_id" not in ctx
