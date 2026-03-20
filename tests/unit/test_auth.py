"""Tests for API key auth dependency — TDD Red Phase.

The auth dependency must:
- Validate X-API-Key header against configured keys (comma-separated)
- Return 401 MISSING_API_KEY if header absent
- Return 403 INVALID_API_KEY if key not in allowed list
- Extract X-User-Id header (default "anonymous")
- Use PRD error format: { error: { code, message } }
- Not affect public endpoints (e.g. /api/health)
"""

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.middleware.auth import require_api_key


def _make_test_app() -> FastAPI:
    """Create a minimal app with one protected route for testing."""
    app = FastAPI()

    @app.get("/protected")
    async def protected(auth: dict = Depends(require_api_key)):
        return {"ok": True, "user_id": auth["user_id"]}

    @app.get("/public")
    async def public():
        return {"public": True}

    return app


@pytest.fixture
def transport():
    app = _make_test_app()
    return ASGITransport(app=app)


class TestAuthDependency:
    """Verify API key validation and user ID extraction."""

    @pytest.mark.asyncio
    async def test_valid_key_returns_200(self, transport):
        """A valid API key should allow access."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/protected",
                headers={"X-API-Key": "dev-key-1"},
            )

        assert response.status_code == 200
        assert response.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_missing_header_returns_401(self, transport):
        """Missing X-API-Key header should return 401."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/protected")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_header_error_code(self, transport):
        """401 response must include MISSING_API_KEY error code."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/protected")

        body = response.json()
        assert body["detail"]["error"]["code"] == "MISSING_API_KEY"

    @pytest.mark.asyncio
    async def test_invalid_key_returns_403(self, transport):
        """An invalid API key should return 403."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/protected",
                headers={"X-API-Key": "wrong-key"},
            )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_key_error_format(self, transport):
        """403 response must follow PRD error format { error: { code, message } }."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/protected",
                headers={"X-API-Key": "wrong-key"},
            )

        body = response.json()
        assert "detail" in body
        assert "error" in body["detail"]
        assert "code" in body["detail"]["error"]
        assert "message" in body["detail"]["error"]
        assert body["detail"]["error"]["code"] == "INVALID_API_KEY"

    @pytest.mark.asyncio
    async def test_user_id_extraction(self, transport):
        """X-User-Id header value should be passed through."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/protected",
                headers={
                    "X-API-Key": "dev-key-1",
                    "X-User-Id": "user-42",
                },
            )

        assert response.json()["user_id"] == "user-42"

    @pytest.mark.asyncio
    async def test_default_user_id_is_anonymous(self, transport):
        """Missing X-User-Id should default to 'anonymous'."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/protected",
                headers={"X-API-Key": "dev-key-1"},
            )

        assert response.json()["user_id"] == "anonymous"

    @pytest.mark.asyncio
    async def test_multiple_configured_keys(self, transport, monkeypatch):
        """Second key in comma-separated API_KEYS should also be valid."""
        monkeypatch.setenv("API_KEYS", "key-alpha,key-beta")

        # Clear cached settings so new env is picked up
        from src.config import get_settings
        get_settings.cache_clear()

        try:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/protected",
                    headers={"X-API-Key": "key-beta"},
                )

            assert response.status_code == 200
        finally:
            # Restore default
            monkeypatch.setenv("API_KEYS", "dev-key-1")
            get_settings.cache_clear()
