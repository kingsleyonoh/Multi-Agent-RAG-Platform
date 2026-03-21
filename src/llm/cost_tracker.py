"""Per-request cost tracking for LLM usage.

Tracks token usage and cost per user with daily budget enforcement.
Uses in-memory storage; can be swapped to Redis for production.

Usage::

    from src.llm.cost_tracker import CostTracker

    tracker = CostTracker()
    tracker.record_cost(model="openai/gpt-4o-mini", tokens_in=100,
                        tokens_out=50, cost_usd=0.001, user_id="u1")
    within_budget = tracker.check_budget("u1", daily_limit=10.0)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import structlog

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
    """In-memory cost tracker with daily budget enforcement.

    Stores cost records keyed by ``(user_id, date)`` for fast
    daily aggregation. Thread-safe for single-process use.
    """

    def __init__(self) -> None:
        # {(user_id, date_str): [CostRecord, ...]}
        self._records: dict[tuple[str, str], list[CostRecord]] = {}

    def record_cost(
        self,
        *,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        user_id: str,
    ) -> CostRecord:
        """Record a cost entry for a user.

        Args:
            model: Model identifier used.
            tokens_in: Prompt tokens.
            tokens_out: Completion tokens.
            cost_usd: Dollar cost for this call.
            user_id: User identifier.

        Returns:
            The created :class:`CostRecord`.
        """
        record = CostRecord(
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            user_id=user_id,
        )
        today = date.today().isoformat()
        key = (user_id, today)
        self._records.setdefault(key, []).append(record)

        logger.debug(
            "cost_recorded",
            model=model,
            cost_usd=cost_usd,
            user_id=user_id,
            daily_total=self.get_user_daily_cost(user_id),
        )
        return record

    def get_user_daily_cost(self, user_id: str) -> float:
        """Get total cost for a user today.

        Args:
            user_id: User identifier.

        Returns:
            Total USD spent today; 0.0 if no records exist.
        """
        today = date.today().isoformat()
        key = (user_id, today)
        records = self._records.get(key, [])
        return sum(r.cost_usd for r in records)

    def check_budget(self, user_id: str, daily_limit: float) -> bool:
        """Check if user is within daily budget.

        Args:
            user_id: User identifier.
            daily_limit: Maximum daily spend in USD.

        Returns:
            True if user's daily spend is under the limit.
        """
        current = self.get_user_daily_cost(user_id)
        return current < daily_limit
