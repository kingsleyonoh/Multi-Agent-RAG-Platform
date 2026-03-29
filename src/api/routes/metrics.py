"""Metrics API endpoints.

Exposes:
  - ``GET /api/metrics/cost``    — total cost, by model, by day
  - ``GET /api/metrics/quality`` — avg relevance, faithfulness, correctness
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import get_cost_tracker

router = APIRouter(tags=["metrics"])


# ── endpoints ────────────────────────────────────────────────────────

@router.get("/cost")
async def cost_metrics(cost_tracker=Depends(get_cost_tracker)):
    """Return cost metrics from the live cost tracker."""
    # Aggregate all records across users
    all_records = []
    for records in cost_tracker._records.values():
        all_records.extend(records)

    total_cost = sum(r.cost_usd for r in all_records)
    by_model: dict[str, float] = {}
    for r in all_records:
        by_model[r.model] = by_model.get(r.model, 0.0) + r.cost_usd

    return {
        "total_cost": round(total_cost, 6),
        "by_model": {k: round(v, 6) for k, v in by_model.items()},
        "total_requests": len(all_records),
    }


@router.get("/quality")
async def quality_metrics():
    """Return quality metrics from evaluation harness."""
    # Seam — wired when evaluation results are persisted
    return {
        "avg_relevance": 0.0,
        "avg_faithfulness": 0.0,
        "avg_correctness": 0.0,
        "total_evaluations": 0,
    }
