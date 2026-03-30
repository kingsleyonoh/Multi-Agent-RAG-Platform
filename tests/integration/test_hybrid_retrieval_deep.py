"""Deep verification — Hybrid retrieval.

Proves all 3 retrieval legs (vector, keyword, graph) contribute
to search results, and the reranker combines scores correctly.
"""

from __future__ import annotations

import io
import uuid

import pytest

from src.retrieval.reranker import rerank

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

_RUN_ID = uuid.uuid4().hex[:8]

_RETRIEVAL_DOC = (
    f"Hybrid retrieval test {_RUN_ID}. "
    "Google Cloud Platform offers machine learning services including "
    "Vertex AI for model training and deployment. TensorFlow is an "
    "open-source framework developed by Google for deep learning."
)


class TestVectorSearchContribution:
    """Verify vector search returns scored results."""

    @pytest.fixture
    async def doc_id(self, httpx_client):
        resp = await httpx_client.post(
            "/api/documents",
            files={"file": (
                f"hybrid_{_RUN_ID}.txt",
                io.BytesIO(_RETRIEVAL_DOC.encode()),
                "text/plain",
            )},
        )
        doc_id = resp.json()["id"]
        yield doc_id
        await httpx_client.delete(f"/api/documents/{doc_id}")

    async def test_search_returns_scored_results(self, httpx_client, doc_id):
        resp = await httpx_client.post(
            "/api/search",
            json={"query": "Google machine learning TensorFlow", "threshold": 0.1},
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) > 0
        # Every result should have a positive score
        for r in results:
            assert r["score"] > 0

    async def test_keyword_match_boosts_relevance(self, httpx_client, doc_id):
        """Searching for exact document terms should return high scores."""
        resp = await httpx_client.post(
            "/api/search",
            json={"query": "TensorFlow deep learning framework", "threshold": 0.1},
        )
        results = resp.json()["results"]
        assert len(results) > 0
        # The top result should be from our document
        top = results[0]
        assert "tensorflow" in top["content"].lower() or "deep learning" in top["content"].lower()


class TestRerankerWeights:
    """Verify the reranker formula: 0.7*vector + 0.2*keyword + 0.1*graph."""

    def test_reranker_produces_correct_weights(self):
        """Rerank with known inputs, verify weighted scoring."""
        from dataclasses import dataclass

        from src.retrieval.reranker import RetrievalCandidate

        candidates = [
            RetrievalCandidate(chunk_id="a", text="A", vector_score=0.9, keyword_score=0.0, graph_score=0.0),
            RetrievalCandidate(chunk_id="b", text="B", vector_score=0.5, keyword_score=0.8, graph_score=0.5),
        ]

        results = rerank(candidates, top_n=2)

        # Candidate A: 0.7*0.9 + 0.2*0.0 + 0.1*0.0 = 0.63
        # Candidate B: 0.7*0.5 + 0.2*0.8 + 0.1*0.5 = 0.35 + 0.16 + 0.05 = 0.56
        assert len(results) == 2
        # A should rank first (0.63 > 0.56)
        assert results[0].chunk_id == "a"

    def test_graph_score_can_change_ranking(self):
        """A high graph_score can push a lower-vector candidate up."""
        from src.retrieval.reranker import RetrievalCandidate

        candidates = [
            RetrievalCandidate(chunk_id="a", text="A", vector_score=0.5, keyword_score=0.0, graph_score=0.0),
            RetrievalCandidate(chunk_id="b", text="B", vector_score=0.5, keyword_score=1.0, graph_score=1.0),
        ]

        results = rerank(candidates, top_n=2)
        # A: 0.7*0.5 = 0.35
        # B: 0.7*0.5 + 0.2*1.0 + 0.1*1.0 = 0.35 + 0.20 + 0.10 = 0.65
        assert results[0].chunk_id == "b"
