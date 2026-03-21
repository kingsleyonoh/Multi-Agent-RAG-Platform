"""Tests for Request ID middleware — TDD Red Phase.

The middleware must:
- Generate UUID4 per request and return it in X-Request-ID header
- Bind request_id to structlog contextvars for log correlation
- Clear structlog context after response (no leaking between requests)
- Honour client-provided X-Request-ID if non-empty
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog
from httpx import ASGITransport, AsyncClient

from src.main import create_app


def _stub_app_state(app):
    """Attach mock service objects so the health route can respond.

    Uses ``return_value`` (not ``side_effect`` lists) so the mocks are
    reusable across multiple requests within the same test.
    """
    mock_conn = AsyncMock()
    # Each .execute() call returns a result with .scalar() → ok value
    mock_conn.execute = AsyncMock(
        return_value=MagicMock(scalar=MagicMock(return_value="vector")),
    )
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    app.state.db_engine = MagicMock()
    app.state.db_engine.connect = MagicMock(return_value=mock_ctx)
    app.state.neo4j_driver = MagicMock()
    app.state.neo4j_driver.verify_connectivity = AsyncMock()
    app.state.redis_client = MagicMock()
    app.state.redis_client.ping = AsyncMock(return_value=True)


@pytest.fixture
def app():
    """Create a fresh FastAPI app with middleware registered and mocked state."""
    _app = create_app()
    _stub_app_state(_app)
    return _app


@pytest.fixture
def transport(app):
    return ASGITransport(app=app)


@pytest.fixture(autouse=True)
def _patch_httpx():
    """Prevent real HTTP calls to the LLM provider during request_id tests."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    inst = AsyncMock()
    inst.get = AsyncMock(return_value=mock_resp)
    inst.__aenter__ = AsyncMock(return_value=inst)
    inst.__aexit__ = AsyncMock(return_value=False)
    with patch("src.api.routes.health.httpx.AsyncClient", return_value=inst):
        yield


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
