"""Relevance scorer — are retrieved chunks relevant to the query?

Uses a testable seam ``_judge`` that defaults to keyword-overlap
heuristics.  In production, override with an LLM-as-judge call.
"""

from __future__ import annotations

from typing import Any


class RelevanceScorer:
    """Score how relevant the retrieved chunks are to the query."""

    def score(self, query: str, chunks: list[str]) -> float:
        """Return a 0–1 relevance score."""
        return self._judge(query, chunks)

    # ── seam ─────────────────────────────────────────────────────────

    @staticmethod
    def _judge(query: str, chunks: list[str]) -> float:
        """Seam — keyword-overlap heuristic (override for LLM judge)."""
        if not chunks:
            return 0.0
        q_words = set(query.lower().split())
        total = 0.0
        for chunk in chunks:
            c_words = set(chunk.lower().split())
            overlap = len(q_words & c_words)
            total += overlap / max(len(q_words), 1)
        return min(total / len(chunks), 1.0)
