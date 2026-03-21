"""Metrics API endpoints.

Exposes:
  - ``GET /api/metrics/cost``    — total cost, by model, by day
  - ``GET /api/metrics/quality`` — avg relevance, faithfulness, correctness
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["metrics"])


# ── seams ────────────────────────────────────────────────────────────

def _get_cost_stats() -> dict:
    """Seam — override in production to query actual cost data."""
    return {
        "total_cost": 0.0,
        "by_model": {},
        "by_day": {},
    }


def _get_quality_stats() -> dict:
    """Seam — override in production to query evaluation history."""
    return {
        "avg_relevance": 0.0,
        "avg_faithfulness": 0.0,
        "avg_correctness": 0.0,
        "total_evaluations": 0,
    }


# ── endpoints ────────────────────────────────────────────────────────

@router.get("/cost")
async def cost_metrics():
    """Return cost metrics."""
    return _get_cost_stats()


@router.get("/quality")
async def quality_metrics():
    """Return quality metrics from evaluation harness."""
    return _get_quality_stats()
