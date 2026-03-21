"""Cost budget reset job.

Resets daily LLM cost budgets for all users at midnight UTC.

Designed to run daily at 00:00 UTC via a scheduler.

Usage::

    from src.jobs.cost_budget_reset import reset_daily_budgets

    count = reset_daily_budgets(tracker)
"""

from __future__ import annotations

from typing import Any


def reset_daily_budgets(tracker: dict[str, dict[str, Any]]) -> int:
    """Reset ``daily_spend`` to 0.0 for every user in *tracker*.

    Args:
        tracker: Mapping of user_id → ``{"daily_spend": float, "budget": float}``.

    Returns:
        Number of users whose budgets were reset.
    """
    count = 0
    for user_data in tracker.values():
        user_data["daily_spend"] = 0.0
        count += 1
    return count
