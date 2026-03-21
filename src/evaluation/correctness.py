"""Correctness scorer — does the response answer the question?

Uses a testable seam ``_judge`` that defaults to a word-overlap
heuristic.  In production, override with an LLM-as-judge call.
"""

from __future__ import annotations


class CorrectnessScorer:
    """Score whether the response answers the query."""

    def score(self, query: str, response: str) -> float:
        """Return a 0–1 correctness score."""
        return self._judge(query, response)

    @staticmethod
    def _judge(query: str, response: str) -> float:
        """Seam — word-overlap heuristic (override for LLM judge)."""
        if not response:
            return 0.0
        q_words = set(query.lower().split())
        r_words = set(response.lower().split())
        overlap = len(q_words & r_words)
        return min(overlap / max(len(q_words), 1), 1.0)
