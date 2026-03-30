"""Hybrid retrieval engine — orchestrates vector, keyword, graph, reranking.

Async implementation that wires actual vector search and graph search
modules into the testable seam architecture.

Usage::

    from src.retrieval.engine import HybridRetrievalEngine

    engine = HybridRetrievalEngine(session=db_session, settings=settings)
    results = await engine.retrieve("What is machine learning?")
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.retrieval.graph_search import search_graph
from src.retrieval.reranker import RetrievalCandidate, rerank
from src.retrieval.vector_search import search as vector_search_fn

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

    Args:
        session: SQLAlchemy async session for vector search.
        settings: App settings with embedding/search configuration.
        neo4j_driver: Optional Neo4j driver for graph expansion.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: object,
        neo4j_driver: object = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._neo4j_driver = neo4j_driver

    # ── Testable seams ───────────────────────────────────────────────

    async def _vector_search(
        self, query: str, query_embedding: list[float], top_k: int,
    ) -> list[RetrievalCandidate]:
        """Seam: vector similarity search via pgvector."""
        threshold = getattr(self._settings, "SIMILARITY_THRESHOLD", 0.7)
        results = await vector_search_fn(
            query_embedding=query_embedding,
            session=self._session,
            top_k=top_k,
            threshold=threshold,
        )
        return [
            RetrievalCandidate(
                chunk_id=str(r.chunk_id),
                text=r.content,
                vector_score=r.score,
            )
            for r in results
        ]

    def _keyword_boost(
        self, query: str, candidates: list[RetrievalCandidate],
    ) -> list[RetrievalCandidate]:
        """Seam: keyword overlap boosting.

        Boosts candidates whose text contains query terms.
        """
        if not candidates or not query.strip():
            return candidates

        query_terms = set(query.lower().split())
        for candidate in candidates:
            text_lower = candidate.text.lower()
            matches = sum(1 for t in query_terms if t in text_lower)
            if query_terms:
                candidate.keyword_score = matches / len(query_terms)
        return candidates

    async def _graph_expand(
        self, query: str, candidates: list[RetrievalCandidate],
    ) -> list[RetrievalCandidate]:
        """Seam: graph-based context expansion via Neo4j."""
        # Extract entity-like terms (capitalised words) from query
        entity_terms = [
            w for w in query.split()
            if w and w[0].isupper() and len(w) > 1
        ]
        if not entity_terms:
            return candidates

        graph_results = await search_graph(query_entities=entity_terms)
        if not graph_results:
            return candidates

        # Boost candidates whose chunk_id appears in graph results
        graph_chunks = set()
        for gr in graph_results:
            graph_chunks.update(gr.related_chunks)

        for candidate in candidates:
            if candidate.chunk_id in graph_chunks:
                candidate.graph_score = 1.0

        return candidates

    # ── Public API ───────────────────────────────────────────────────

    async def retrieve(
        self,
        query: str,
        query_embedding: list[float],
        top_n: int = 5,
    ) -> list[RetrievalResult]:
        """Execute the full hybrid retrieval pipeline.

        1. Vector search
        2. Keyword boost
        3. Graph expansion
        4. Reranking

        Args:
            query: User query string.
            query_embedding: Pre-computed query embedding.
            top_n: Maximum results to return.

        Returns:
            Top-N RetrievalResult objects.
        """
        if not query or not query.strip():
            return []

        top_k = getattr(self._settings, "RETRIEVAL_TOP_K", 10)

        # 1. Vector search
        candidates = await self._vector_search(query, query_embedding, top_k)

        # 2. Keyword boost
        candidates = self._keyword_boost(query, candidates)

        # 3. Graph expansion
        candidates = await self._graph_expand(query, candidates)

        # 4. Reranking
        if not candidates:
            return []

        rerank_top_n = getattr(self._settings, "RERANK_TOP_N", top_n)
        ranked = rerank(candidates, top_n=rerank_top_n)

        results = [
            RetrievalResult(
                chunk_id=c.chunk_id,
                text=c.text,
                score=c.final_score,
            )
            for c in ranked
        ]

        logger.debug(
            "hybrid_retrieval", query_len=len(query), results=len(results),
        )
        return results
