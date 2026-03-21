"""Cache statistics API endpoint.

Exposes ``GET /api/cache/stats`` returning total entries, hit rate, and
estimated cost saved by the semantic cache.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["cache"])


# ── seam ─────────────────────────────────────────────────────────────

def _get_cache_stats() -> dict:
    """Seam — override in production to read from a real cache instance."""
    return {
        "total_entries": 0,
        "total_lookups": 0,
        "total_hits": 0,
        "hit_rate": 0.0,
        "estimated_cost_saved": 0.0,
    }


# ── endpoint ─────────────────────────────────────────────────────────

@router.get("/stats")
async def cache_stats():
    """Return semantic-cache statistics."""
    return _get_cache_stats()
