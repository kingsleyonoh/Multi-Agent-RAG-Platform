"""Evaluation harness — orchestrates all three scorers.

After each RAG response the caller invokes :func:`evaluate` which runs
relevance, faithfulness, and correctness scoring, flags low-quality
responses, and stores the result in an in-memory history list.
"""

from __future__ import annotations

from typing import Any

from src.evaluation.relevance import RelevanceScorer
from src.evaluation.faithfulness import FaithfulnessScorer
from src.evaluation.correctness import CorrectnessScorer


class EvaluationHarness:
    """Run all quality metrics and flag responses below threshold."""

    def __init__(self, *, min_threshold: float = 0.7) -> None:
        self.min_threshold = min_threshold
        self.history: list[dict[str, Any]] = []
        self._relevance = RelevanceScorer()
        self._faithfulness = FaithfulnessScorer()
        self._correctness = CorrectnessScorer()

    def evaluate(
        self,
        query: str,
        response: str,
        chunks: list[str],
    ) -> dict[str, Any]:
        """Score a single RAG response and return the result dict."""
        rel = self._relevance.score(query=query, chunks=chunks)
        faith = self._faithfulness.score(response=response, chunks=chunks)
        corr = self._correctness.score(query=query, response=response)

        avg = (rel + faith + corr) / 3
        flagged = avg < self.min_threshold

        result: dict[str, Any] = {
            "relevance": round(rel, 4),
            "faithfulness": round(faith, 4),
            "correctness": round(corr, 4),
            "average": round(avg, 4),
            "flagged": flagged,
        }
        self.history.append(result)
        return result
