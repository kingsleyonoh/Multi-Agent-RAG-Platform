"""Per-request cost tracking for LLM usage.

Tracks token usage and cost per user with daily budget enforcement.
Persists to the ``cost_logs`` table in PostgreSQL so data survives
server restarts.  Falls back to in-memory tracking when no session
factory is available (e.g. tests).

Usage::

    from src.llm.cost_tracker import CostTracker

    tracker = CostTracker(session_factory=get_session_factory(engine))
    await tracker.record_cost(model="openai/gpt-4o-mini", tokens_in=100,
                              tokens_out=50, cost_usd=0.001, user_id="u1")
    within_budget = await tracker.check_budget("u1", daily_limit=10.0)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CostRecord:
    """A single cost observation from an LLM call."""

    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    user_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CostTracker:
    """DB-backed cost tracker with daily budget enforcement.

    When a session factory is provided, records persist to the
    ``cost_logs`` table.  Without one, falls back to in-memory
    storage (useful for tests).
    """

    def __init__(self, session_factory: async_sessionmaker | None = None) -> None:
        self._session_factory = session_factory
        # In-memory fallback when DB is unavailable
        self._memory: dict[tuple[str, str], list[CostRecord]] = {}

    async def record_cost(
        self,
        *,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        user_id: str,
    ) -> CostRecord:
        """Record a cost entry for a user.

        Writes to the ``cost_logs`` table if DB is available,
        otherwise stores in memory.
        """
        record = CostRecord(
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            user_id=user_id,
        )

        if self._session_factory is not None:
            try:
                from src.db.models import CostLog

                async with self._session_factory() as session:
                    session.add(CostLog(
                        user_id=user_id,
                        model=model,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost_usd=cost_usd,
                    ))
                    await session.commit()
            except Exception:
                logger.warning("cost_log_db_write_failed", exc_info=True)
                # Fall back to in-memory
                self._record_memory(record)
        else:
            self._record_memory(record)

        logger.debug(
            "cost_recorded",
            model=model,
            cost_usd=cost_usd,
            user_id=user_id,
        )
        return record

    async def get_user_daily_cost(self, user_id: str) -> float:
        """Get total cost for a user today."""
        if self._session_factory is not None:
            try:
                async with self._session_factory() as session:
                    result = await session.execute(
                        text(
                            "SELECT COALESCE(SUM(cost_usd), 0) "
                            "FROM cost_logs "
                            "WHERE user_id = :uid "
                            "AND created_at >= CURRENT_DATE"
                        ),
                        {"uid": user_id},
                    )
                    return float(result.scalar())
            except Exception:
                logger.warning("cost_log_db_read_failed", exc_info=True)

        # In-memory fallback
        today = date.today().isoformat()
        records = self._memory.get((user_id, today), [])
        return sum(r.cost_usd for r in records)

    async def check_budget(self, user_id: str, daily_limit: float) -> bool:
        """Check if user is within daily budget.

        Returns True if user's daily spend is under the limit.
        """
        current = await self.get_user_daily_cost(user_id)
        return current < daily_limit

    async def get_aggregate_metrics(self) -> dict:
        """Return aggregate cost metrics for the metrics API."""
        if self._session_factory is not None:
            try:
                async with self._session_factory() as session:
                    # Total cost and request count
                    totals = await session.execute(text(
                        "SELECT COALESCE(SUM(cost_usd), 0) AS total_cost, "
                        "COUNT(*) AS total_requests "
                        "FROM cost_logs"
                    ))
                    row = totals.one()

                    # By model breakdown
                    by_model_result = await session.execute(text(
                        "SELECT model, SUM(cost_usd) AS cost, COUNT(*) AS requests "
                        "FROM cost_logs GROUP BY model ORDER BY cost DESC"
                    ))
                    by_model = {
                        r.model: {"cost": float(r.cost), "requests": r.requests}
                        for r in by_model_result.all()
                    }

                    return {
                        "total_cost": float(row.total_cost),
                        "total_requests": row.total_requests,
                        "by_model": by_model,
                    }
            except Exception:
                logger.warning("cost_metrics_db_read_failed", exc_info=True)

        # In-memory fallback
        total_cost = 0.0
        total_requests = 0
        by_model: dict[str, dict] = {}
        for records in self._memory.values():
            for r in records:
                total_cost += r.cost_usd
                total_requests += 1
                if r.model not in by_model:
                    by_model[r.model] = {"cost": 0.0, "requests": 0}
                by_model[r.model]["cost"] += r.cost_usd
                by_model[r.model]["requests"] += 1

        return {
            "total_cost": round(total_cost, 6),
            "total_requests": total_requests,
            "by_model": by_model,
        }

    def _record_memory(self, record: CostRecord) -> None:
        """Store a cost record in memory (fallback)."""
        today = date.today().isoformat()
        key = (record.user_id, today)
        self._memory.setdefault(key, []).append(record)
