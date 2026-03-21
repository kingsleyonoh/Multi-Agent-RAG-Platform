"""Reranker — weighted scoring of retrieval candidates.

Combines vector similarity, keyword overlap, and graph relevance
using configurable weights.

Usage::

    from src.retrieval.reranker import rerank, RetrievalCandidate

    candidates = [RetrievalCandidate(...)]
    ranked = rerank(candidates, top_n=5)
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

# Default reranking weights
_DEFAULT_VECTOR_WEIGHT = 0.7
_DEFAULT_KEYWORD_WEIGHT = 0.2
_DEFAULT_GRAPH_WEIGHT = 0.1


@dataclass
class RetrievalCandidate:
    """A retrieval result candidate for reranking."""

    chunk_id: str
    text: str
    vector_score: float = 0.0
    keyword_score: float = 0.0
    graph_score: float = 0.0
    final_score: float = 0.0


def rerank(
    candidates: list[RetrievalCandidate],
    top_n: int = 5,
    vector_weight: float = _DEFAULT_VECTOR_WEIGHT,
    keyword_weight: float = _DEFAULT_KEYWORD_WEIGHT,
    graph_weight: float = _DEFAULT_GRAPH_WEIGHT,
) -> list[RetrievalCandidate]:
    """Score and rerank retrieval candidates.

    Args:
        candidates: List of candidates to rank.
        top_n: Maximum results to return.
        vector_weight: Weight for vector similarity score.
        keyword_weight: Weight for keyword overlap score.
        graph_weight: Weight for graph relevance score.

    Returns:
        Top-N candidates sorted by final_score descending.
    """
    if not candidates:
        return []

    for c in candidates:
        c.final_score = (
            vector_weight * c.vector_score
            + keyword_weight * c.keyword_score
            + graph_weight * c.graph_score
        )

    ranked = sorted(candidates, key=lambda c: c.final_score, reverse=True)
    result = ranked[:top_n]

    logger.debug(
        "reranked",
        total=len(candidates),
        returned=len(result),
        top_score=result[0].final_score if result else 0.0,
    )
    return result
