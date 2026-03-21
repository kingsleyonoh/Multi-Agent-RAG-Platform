"""Faithfulness scorer — is the response grounded in source chunks?

Uses a testable seam ``_judge`` that defaults to word-overlap heuristic.
In production, override with LLM-based claim extraction + verification.
"""

from __future__ import annotations


class FaithfulnessScorer:
    """Score how faithful the response is to the source material."""

    def score(self, response: str, chunks: list[str]) -> float:
        """Return a 0–1 faithfulness score."""
        return self._judge(response, chunks)

    @staticmethod
    def _judge(response: str, chunks: list[str]) -> float:
        """Seam — word-overlap heuristic (override for LLM judge)."""
        if not chunks or not response:
            return 0.0
        r_words = set(response.lower().split())
        all_chunk_words: set[str] = set()
        for c in chunks:
            all_chunk_words.update(c.lower().split())
        overlap = len(r_words & all_chunk_words)
        return min(overlap / max(len(r_words), 1), 1.0)
