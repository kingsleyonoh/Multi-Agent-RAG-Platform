"""Cache statistics API endpoint.

Exposes ``GET /api/cache/stats`` returning total entries, hit rate, and
estimated cost saved by the semantic cache.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import get_semantic_cache

router = APIRouter(tags=["cache"])


# ── endpoint ─────────────────────────────────────────────────────────

@router.get("/stats")
async def cache_stats(cache=Depends(get_semantic_cache)):
    """Return semantic-cache statistics from the live cache instance."""
    return cache.get_stats()
