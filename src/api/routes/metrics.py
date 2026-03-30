"""Metrics API endpoints.

Exposes:
  - ``GET /api/metrics/cost``    — total cost, by model, by day
  - ``GET /api/metrics/quality`` — avg relevance, faithfulness, correctness
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_cost_tracker, get_db_session
from src.db.models import Evaluation

router = APIRouter(tags=["metrics"])


# ── endpoints ────────────────────────────────────────────────────────

@router.get("/cost")
async def cost_metrics(cost_tracker=Depends(get_cost_tracker)):
    """Return cost metrics from the cost tracker (DB-backed)."""
    return await cost_tracker.get_aggregate_metrics()


@router.get("/quality")
async def quality_metrics(
    session: AsyncSession = Depends(get_db_session),
):
    """Return quality metrics from the evaluations table.

    Aggregates average score per metric type (relevance,
    faithfulness, correctness) and total evaluation count.
    """
    stmt = (
        select(
            Evaluation.metric,
            func.avg(Evaluation.score).label("avg_score"),
            func.count().label("cnt"),
        )
        .group_by(Evaluation.metric)
    )
    result = await session.execute(stmt)
    rows = result.all()

    metrics: dict[str, float] = {}
    total = 0
    for row in rows:
        metrics[row[0]] = round(float(row[1]), 4)
        total += row[2]

    return {
        "avg_relevance": metrics.get("relevance", 0.0),
        "avg_faithfulness": metrics.get("faithfulness", 0.0),
        "avg_correctness": metrics.get("correctness", 0.0),
        "total_evaluations": total,
    }
