"""Tests for error handling middleware — TDD Red Phase.

The error handlers must:
- Normalize HTTPException to PRD format { error: { code, message } }
- Preserve HTTP status codes
- Handle auth-shaped HTTPException detail correctly
- Format validation errors with VALIDATION_ERROR code and details array
- Include traceback in dev, suppress in production
- Keep all error responses consistent
- Not affect normal (non-error) responses
"""

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from src.api.middleware.errors import register_error_handlers


def _make_test_app(env: str = "development") -> FastAPI:
    """Create a minimal app with error handlers registered."""
    app = FastAPI()
    register_error_handlers(app, env=env)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.get("/not-found")
    async def not_found():
        raise HTTPException(status_code=404, detail="Resource not found")

    @app.get("/auth-error")
    async def auth_error():
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "MISSING_API_KEY",
                    "message": "X-API-Key header is required.",
                },
            },
        )

    @app.get("/crash")
    async def crash():
        raise RuntimeError("Something broke internally")

    class ItemCreate(BaseModel):
        name: str
        count: int

    @app.post("/validate")
    async def validate(item: ItemCreate):
        return {"name": item.name}

    return app


@pytest.fixture
def dev_transport():
    return ASGITransport(app=_make_test_app(env="development"))


@pytest.fixture
def prod_transport():
    return ASGITransport(app=_make_test_app(env="production"))


class TestErrorHandlers:
    """Verify error response normalization."""

    @pytest.mark.asyncio
    async def test_http_exception_prd_format(self, dev_transport):
        """HTTPException should produce { error: { code, message } }."""
        async with AsyncClient(transport=dev_transport, base_url="http://test") as client:
            response = await client.get("/not-found")

        body = response.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]

    @pytest.mark.asyncio
    async def test_http_exception_preserves_status(self, dev_transport):
        """HTTPException status code should be preserved."""
        async with AsyncClient(transport=dev_transport, base_url="http://test") as client:
            response = await client.get("/not-found")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_auth_exception_unwrapped(self, dev_transport):
        """Auth-style HTTPException with nested error dict should be unwrapped."""
        async with AsyncClient(transport=dev_transport, base_url="http://test") as client:
            response = await client.get("/auth-error")

        body = response.json()
        assert body["error"]["code"] == "MISSING_API_KEY"
        assert body["error"]["message"] == "X-API-Key header is required."

    @pytest.mark.asyncio
    async def test_validation_error_format(self, dev_transport):
        """Validation errors should return 422 with VALIDATION_ERROR code."""
        async with AsyncClient(transport=dev_transport, base_url="http://test") as client:
            response = await client.post(
                "/validate",
                json={"name": 123},  # count is missing, name should be str
            )

        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "details" in body["error"]
        assert isinstance(body["error"]["details"], list)

    @pytest.mark.asyncio
    async def test_unhandled_exception_dev_has_traceback(self, dev_transport):
        """In development, unhandled exceptions should include traceback."""
        async with AsyncClient(transport=dev_transport, base_url="http://test") as client:
            response = await client.get("/crash")

        assert response.status_code == 500
        body = response.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
        assert "details" in body["error"]
        # details should contain traceback info
        assert len(body["error"]["details"]) > 0

    @pytest.mark.asyncio
    async def test_unhandled_exception_prod_no_traceback(self, prod_transport):
        """In production, unhandled exceptions must NOT leak tracebacks."""
        async with AsyncClient(transport=prod_transport, base_url="http://test") as client:
            response = await client.get("/crash")

        assert response.status_code == 500
        body = response.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
        assert "details" not in body["error"] or body["error"].get("details") is None

    @pytest.mark.asyncio
    async def test_error_format_consistency(self, dev_transport):
        """All error responses must have error.code and error.message keys."""
        async with AsyncClient(transport=dev_transport, base_url="http://test") as client:
            r404 = await client.get("/not-found")
            r500 = await client.get("/crash")
            r422 = await client.post("/validate", json={})

        for resp in [r404, r500, r422]:
            body = resp.json()
            assert "error" in body, f"Missing 'error' key in {resp.status_code} response"
            assert "code" in body["error"], f"Missing 'code' in {resp.status_code} error"
            assert "message" in body["error"], f"Missing 'message' in {resp.status_code} error"

    @pytest.mark.asyncio
    async def test_success_response_unaffected(self, dev_transport):
        """Normal 200 responses should not be wrapped in error format."""
        async with AsyncClient(transport=dev_transport, base_url="http://test") as client:
            response = await client.get("/ok")

        assert response.status_code == 200
        body = response.json()
        assert body == {"status": "ok"}
        assert "error" not in body
