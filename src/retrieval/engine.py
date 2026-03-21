"""Hybrid retrieval engine — orchestrates vector, keyword, graph, reranking.

Provides testable seams for each retrieval stage.

Usage::

    from src.retrieval.engine import HybridRetrievalEngine

    engine = HybridRetrievalEngine()
    results = engine.retrieve("What is machine learning?")
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from src.retrieval.reranker import RetrievalCandidate, rerank

logger = structlog.get_logger(__name__)


@dataclass
class RetrievalResult:
    """A final retrieval result."""

    chunk_id: str
    text: str
    score: float
    source_metadata: dict = field(default_factory=dict)


class HybridRetrievalEngine:
    """Orchestrate vector → keyword → graph → reranking retrieval.

    Each stage has a testable seam method that can be overridden.
    """

    # ── Testable seams ───────────────────────────────────────────────

    def _vector_search(self, query: str) -> list[RetrievalCandidate]:
        """Seam: vector similarity search."""
        return []

    def _keyword_boost(
        self, query: str, candidates: list[RetrievalCandidate]
    ) -> list[RetrievalCandidate]:
        """Seam: keyword overlap boosting."""
        return candidates

    def _graph_expand(
        self, query: str, candidates: list[RetrievalCandidate]
    ) -> list[RetrievalCandidate]:
        """Seam: graph-based context expansion."""
        return candidates

    # ── Public API ───────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        top_n: int = 5,
    ) -> list[RetrievalResult]:
        """Execute the full hybrid retrieval pipeline.

        1. Vector search
        2. Keyword boost
        3. Graph expansion
        4. Reranking

        Args:
            query: User query string.
            top_n: Maximum results to return.

        Returns:
            Top-N RetrievalResult objects.
        """
        if not query or not query.strip():
            return []

        # 1. Vector search
        candidates = self._vector_search(query)

        # 2. Keyword boost
        candidates = self._keyword_boost(query, candidates)

        # 3. Graph expansion
        candidates = self._graph_expand(query, candidates)

        # 4. Reranking
        if not candidates:
            return []

        ranked = rerank(candidates, top_n=top_n)

        results = [
            RetrievalResult(
                chunk_id=c.chunk_id,
                text=c.text,
                score=c.final_score,
            )
            for c in ranked
        ]

        logger.debug("hybrid_retrieval", query_len=len(query), results=len(results))
        return results
