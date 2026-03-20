"""Request ID middleware — generates or propagates a unique ID per request.

Every inbound request receives a UUID4 identifier that is:
- Bound to structlog contextvars for automatic log correlation.
- Returned in the ``X-Request-ID`` response header.
- Accepted from the client (``X-Request-ID`` header) for distributed tracing.
"""

import uuid
from typing import Any, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request/response cycle."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Any],
    ) -> Response:
        # Use client-provided ID if non-empty, else generate one.
        client_id = (request.headers.get(_HEADER) or "").strip()
        request_id = client_id if client_id else str(uuid.uuid4())

        # Bind to structlog for log correlation.
        structlog.contextvars.bind_contextvars(request_id=request_id)

        try:
            response: Response = await call_next(request)
            response.headers[_HEADER] = request_id
            return response
        finally:
            structlog.contextvars.clear_contextvars()
