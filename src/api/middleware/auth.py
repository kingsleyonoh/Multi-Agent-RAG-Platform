"""API key authentication dependency.

Validates ``X-API-Key`` header against the configured key list and extracts
the optional ``X-User-Id`` header for per-user cost tracking.

Usage::

    from src.api.middleware.auth import require_api_key

    @router.get("/protected")
    async def protected(auth: dict = Depends(require_api_key)):
        user_id = auth["user_id"]
        ...
"""

from fastapi import HTTPException, Request

from src.config import get_settings


async def require_api_key(request: Request) -> dict:
    """FastAPI dependency — reject requests without a valid API key.

    Returns
    -------
    dict
        ``{"api_key": str, "user_id": str}`` on success.

    Raises
    ------
    HTTPException 401
        ``X-API-Key`` header is missing.
    HTTPException 403
        ``X-API-Key`` value is not in the configured ``API_KEYS``.
    """
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "MISSING_API_KEY",
                    "message": "X-API-Key header is required.",
                },
            },
        )

    settings = get_settings()
    valid_keys = [k.strip() for k in settings.API_KEYS.split(",")]

    if api_key not in valid_keys:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "The provided API key is not valid.",
                },
            },
        )

    user_id = (request.headers.get("X-User-Id") or "").strip() or "anonymous"

    return {"api_key": api_key, "user_id": user_id}
