"""Global error handlers that normalise all exceptions to the PRD format.

Response shape::

    {
        "error": {
            "code":    "<UPPER_SNAKE>",
            "message": "<human-readable>",
            "details": [...]          // optional — validation or traceback
        }
    }

Usage::

    from src.api.middleware.errors import register_error_handlers
    register_error_handlers(app)
"""

from __future__ import annotations

import traceback
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# ── Helpers ──────────────────────────────────────────────────────────

_STATUS_CODE_MAP: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    429: "RATE_LIMIT_EXCEEDED",
}


def _error_body(
    code: str,
    message: str,
    details: list[Any] | None = None,
) -> dict:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


# ── Handlers ─────────────────────────────────────────────────────────


async def _http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Normalise ``HTTPException`` to PRD error format.

    If ``detail`` is already shaped as ``{"error": {"code", "message"}}``,
    it is used directly (e.g. from auth / rate-limit middleware).
    Otherwise the status code is mapped to a generic code.
    """
    detail = exc.detail

    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=detail,
        )

    code = _STATUS_CODE_MAP.get(exc.status_code, "HTTP_ERROR")
    message = detail if isinstance(detail, str) else str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code, message),
    )


async def _validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return 422 with ``VALIDATION_ERROR`` code and structured details."""
    return JSONResponse(
        status_code=422,
        content=_error_body(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            details=exc.errors(),
        ),
    )


# ── Catch-all middleware ─────────────────────────────────────────────


class _CatchAllMiddleware(BaseHTTPMiddleware):
    """Intercept unhandled exceptions before Starlette's ServerErrorMiddleware.

    Starlette's built-in ``ServerErrorMiddleware`` catches bare ``Exception``
    subclasses before FastAPI's ``app.add_exception_handler(Exception, …)``
    fires.  Using a real middleware ensures we always control the 500 body.
    """

    def __init__(self, app: Any, env: str = "production") -> None:
        super().__init__(app)
        self._env = env

    async def dispatch(self, request: Request, call_next):  # noqa: ANN001
        try:
            return await call_next(request)
        except Exception as exc:
            details: list[str] | None = None
            if self._env != "production":
                details = traceback.format_exception(
                    type(exc), exc, exc.__traceback__,
                )
            return JSONResponse(
                status_code=500,
                content=_error_body(
                    code="INTERNAL_ERROR",
                    message="Internal server error.",
                    details=details,
                ),
            )


# ── Registration ─────────────────────────────────────────────────────


def register_error_handlers(app: FastAPI, *, env: str = "production") -> None:
    """Attach all exception handlers to *app*."""

    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)

    # Middleware catches unhandled exceptions (runs before ServerErrorMiddleware)
    app.add_middleware(_CatchAllMiddleware, env=env)
