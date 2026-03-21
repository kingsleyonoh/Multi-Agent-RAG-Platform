"""Evaluation aggregation job.

Pre-computes aggregate quality metrics from the
:class:`EvaluationHarness` history.

Designed to run every 24 hours via a scheduler.

Usage::

    from src.jobs.evaluation_aggregation import aggregate_metrics

    agg = aggregate_metrics(harness.history)
"""

from __future__ import annotations

from typing import Any


def aggregate_metrics(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute average quality metrics from evaluation *history*.

    Returns a dict with ``avg_relevance``, ``avg_faithfulness``,
    ``avg_correctness``, ``total_evaluations``, and ``flagged_count``.
    """
    total = len(history)
    if total == 0:
        return {
            "avg_relevance": 0.0,
            "avg_faithfulness": 0.0,
            "avg_correctness": 0.0,
            "total_evaluations": 0,
            "flagged_count": 0,
        }

    avg_rel = sum(h["relevance"] for h in history) / total
    avg_faith = sum(h["faithfulness"] for h in history) / total
    avg_corr = sum(h["correctness"] for h in history) / total
    flagged = sum(1 for h in history if h.get("flagged", False))

    return {
        "avg_relevance": round(avg_rel, 4),
        "avg_faithfulness": round(avg_faith, 4),
        "avg_correctness": round(avg_corr, 4),
        "total_evaluations": total,
        "flagged_count": flagged,
    }
