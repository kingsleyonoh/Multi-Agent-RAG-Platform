"""Batch 11 RED tests — Knowledge Graph Integration.

Tests for:
- Entity extraction during ingestion (entity_extractor.py)
- Graph search (graph_search.py)
- Reranker (reranker.py)
- Hybrid retrieval engine (engine.py)
- Graph API endpoints (graph.py)
"""

import pytest
from dataclasses import dataclass


# ── Entity extraction during ingestion ───────────────────────────────

class TestEntityExtractor:
    """Extract entities from document chunks and upsert to graph."""

    def test_extract_entities_from_chunk(self):
        from src.ingestion.entity_extractor import extract_entities
        entities = extract_entities(
            "Google announced a partnership with Microsoft in January 2024."
        )
        assert len(entities) > 0

    def test_entity_has_required_fields(self):
        from src.ingestion.entity_extractor import extract_entities
        entities = extract_entities("Apple released new products.")
        for e in entities:
            assert hasattr(e, "type")
            assert hasattr(e, "value")

    def test_empty_text_returns_empty(self):
        from src.ingestion.entity_extractor import extract_entities
        assert extract_entities("") == []

    def test_upsert_entities_callable(self):
        from src.ingestion.entity_extractor import upsert_entities
        # Should not raise — uses _run_cypher seam (no-op by default)
        from src.ingestion.entity_extractor import ExtractedEntity
        entities = [ExtractedEntity(type="organization", value="Google")]
        upsert_entities(entities, document_id="doc_1")


# ── Graph search ─────────────────────────────────────────────────────

class TestGraphSearch:
    """Query Neo4j for entities related to query."""

    @pytest.mark.asyncio
    async def test_search_returns_list(self):
        from src.retrieval.graph_search import search_graph
        results = await search_graph(query_entities=["Google"])
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self):
        from src.retrieval.graph_search import search_graph
        results = await search_graph(query_entities=[])
        assert results == []

    def test_result_has_entity_and_chunks(self):
        from src.retrieval.graph_search import search_graph, GraphResult
        # Just verify the type exists and structure
        r = GraphResult(entity="Google", related_chunks=["chunk1"])
        assert r.entity == "Google"
        assert len(r.related_chunks) == 1


# ── Reranker ─────────────────────────────────────────────────────────

class TestReranker:
    """Score and rerank retrieval results."""

    def test_rerank_returns_sorted(self):
        from src.retrieval.reranker import rerank, RetrievalCandidate
        candidates = [
            RetrievalCandidate(
                chunk_id="a", text="low", vector_score=0.3,
                keyword_score=0.1, graph_score=0.0,
            ),
            RetrievalCandidate(
                chunk_id="b", text="high", vector_score=0.9,
                keyword_score=0.5, graph_score=0.2,
            ),
        ]
        ranked = rerank(candidates)
        assert ranked[0].chunk_id == "b"

    def test_rerank_default_weights(self):
        from src.retrieval.reranker import rerank, RetrievalCandidate
        c = RetrievalCandidate(
            chunk_id="x", text="test", vector_score=1.0,
            keyword_score=1.0, graph_score=1.0,
        )
        ranked = rerank([c])
        # 0.7*1.0 + 0.2*1.0 + 0.1*1.0 = 1.0
        assert abs(ranked[0].final_score - 1.0) < 0.01

    def test_rerank_empty_input(self):
        from src.retrieval.reranker import rerank
        assert rerank([]) == []

    def test_top_n_limit(self):
        from src.retrieval.reranker import rerank, RetrievalCandidate
        candidates = [
            RetrievalCandidate(
                chunk_id=f"c{i}", text=f"text{i}",
                vector_score=i/10, keyword_score=0.0, graph_score=0.0,
            )
            for i in range(10)
        ]
        ranked = rerank(candidates, top_n=3)
        assert len(ranked) == 3


# ── Hybrid retrieval engine ──────────────────────────────────────────

class TestHybridRetrievalEngine:
    """Orchestrate vector + keyword + graph + reranking."""

    @pytest.mark.asyncio
    async def test_retrieve_returns_list(self):
        from unittest.mock import AsyncMock, MagicMock, patch

        from src.retrieval.engine import HybridRetrievalEngine

        mock_session = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.SIMILARITY_THRESHOLD = 0.7
        mock_settings.RETRIEVAL_TOP_K = 10
        mock_settings.RERANK_TOP_N = 5
        engine = HybridRetrievalEngine(
            session=mock_session, settings=mock_settings,
        )
        with patch.object(engine, "_vector_search", new_callable=AsyncMock, return_value=[]):
            results = await engine.retrieve(
                "What is machine learning?", query_embedding=[0.1] * 1536,
            )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_retrieve_empty_query(self):
        from unittest.mock import AsyncMock, MagicMock

        from src.retrieval.engine import HybridRetrievalEngine

        mock_session = AsyncMock()
        mock_settings = MagicMock()
        engine = HybridRetrievalEngine(
            session=mock_session, settings=mock_settings,
        )
        results = await engine.retrieve("", query_embedding=[])
        assert results == []


# ── Graph API endpoints ──────────────────────────────────────────────

class TestGraphAPIEndpoints:
    """Graph entity API routes."""

    def test_entities_endpoint_exists(self):
        from src.api.routes.graph import router
        paths = [r.path for r in router.routes]
        assert "/entities" in paths

    def test_related_endpoint_exists(self):
        from src.api.routes.graph import router
        paths = [r.path for r in router.routes]
        assert "/related/{entity_id}" in paths
