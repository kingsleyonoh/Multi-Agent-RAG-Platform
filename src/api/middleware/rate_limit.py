"""Rate limiting middleware — fixed-window Redis counter.

Uses ``INCR`` + ``EXPIRE`` per ``api_key:path:minute`` to enforce
per-endpoint limits from PRD §8b.  Fails open when Redis is
unreachable so the API degrades gracefully.

Public API
----------
RateLimitMiddleware  — Starlette ``BaseHTTPMiddleware`` subclass.
"""

from __future__ import annotations

import logging
import re
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from src.config import get_settings
from src.db.redis import get_client

logger = logging.getLogger(__name__)


# ── Per-endpoint rate limits (PRD §8b) ──────────────────────────
# Key = (HTTP method regex, path regex) → value = requests per minute.
# Order matters — first match wins.  Default fallback at the end.

_RATE_LIMITS: list[tuple[str, str, int]] = [
    ("POST", r"^/api/chat$",               60),
    ("POST", r"^/api/chat/sync$",           30),
    ("POST", r"^/api/documents$",           20),
    ("POST", r"^/api/documents/url$",       10),
    ("GET",  r"^/api/documents$",          100),
    ("GET",  r"^/api/documents/[^/]+$",    100),
    ("DELETE", r"^/api/documents/[^/]+$",   20),
    ("POST", r"^/api/search$",            200),
    ("GET",  r"^/api/conversations$",     100),
    ("GET",  r"^/api/conversations/[^/]+$", 100),
    ("DELETE", r"^/api/conversations/[^/]+$", 20),
    ("GET",  r"^/api/graph/",              50),
    ("POST", r"^/api/prompts$",            20),
    ("GET",  r"^/api/prompts$",           100),
    ("PUT",  r"^/api/prompts/[^/]+$",      20),
    ("GET",  r"^/api/metrics/",            30),
    ("GET",  r"^/api/cache/stats$",        30),
]

_DEFAULT_LIMIT = 60  # fallback for unmatched routes

# Routes exempt from rate limiting
_EXEMPT_PATHS = {"/api/health"}


def _get_limit(method: str, path: str) -> int:
    """Return the per-minute limit for the given method + path."""
    for rule_method, pattern, limit in _RATE_LIMITS:
        if method.upper() == rule_method and re.match(pattern, path):
            return limit
    return _DEFAULT_LIMIT


def _get_redis_client():
    """Return the shared Redis async client.

    Separated for easy patching in unit tests.
    """
    settings = get_settings()
    return get_client(settings.REDIS_URL)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window rate limiter backed by Redis ``INCR`` + ``EXPIRE``."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path

        # Exempt paths bypass rate limiting entirely
        if path in _EXEMPT_PATHS:
            return await call_next(request)

        method = request.method
        limit = _get_limit(method, path)
        api_key = request.headers.get("X-API-Key", "anonymous")
        minute_bucket = int(time.time()) // 60
        redis_key = f"ratelimit:{api_key}:{path}:{minute_bucket}"

        try:
            redis = _get_redis_client()
            count = await redis.incr(redis_key)

            if count == 1:
                await redis.expire(redis_key, 60)

            ttl = await redis.ttl(redis_key)
            reset_at = int(time.time()) + max(ttl, 0)
            remaining = max(limit - count, 0)

        except Exception:  # noqa: BLE001
            logger.warning(
                "Redis unavailable for rate limiting — failing open",
                exc_info=True,
            )
            # Fail-open: let the request through without headers
            return await call_next(request)

        # Build rate-limit headers
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_at),
        }

        if count > limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit of {limit}/min exceeded. Try again later.",
                    },
                },
                headers={**headers, "Retry-After": str(max(ttl, 1))},
            )

        # Under limit — proceed and add headers to the response
        response = await call_next(request)
        for key, value in headers.items():
            response.headers[key] = value
        return response
