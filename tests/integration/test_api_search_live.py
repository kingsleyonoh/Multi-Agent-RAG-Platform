"""L3 — Search API integration tests.

Tests vector similarity search against the live server
with real pgvector queries and OpenRouter embeddings.
"""

from __future__ import annotations

import io
import uuid

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

_RUN_ID = uuid.uuid4().hex[:8]

_SEARCH_DOC_CONTENT = (
    f"Search test document {_RUN_ID}. "
    "Python is a high-level programming language created by Guido van Rossum "
    "in 1991. It emphasizes code readability with significant whitespace. "
    "Python is widely used in artificial intelligence, data science, "
    "web development, and automation."
)


@pytest.fixture(scope="module")
def _search_doc_id():
    """Will be set by the first test that uploads."""
    return {}


class TestSearchAPI:
    """Search endpoint against live server with ingested document."""

    @pytest.fixture(autouse=True)
    async def _ensure_document(self, httpx_client, _search_doc_id):
        """Upload a document once for all search tests."""
        if "id" not in _search_doc_id:
            resp = await httpx_client.post(
                "/api/documents",
                files={"file": (
                    f"search_{_RUN_ID}.txt",
                    io.BytesIO(_SEARCH_DOC_CONTENT.encode()),
                    "text/plain",
                )},
            )
            _search_doc_id["id"] = resp.json()["id"]
        yield
        # Don't cleanup here — let the whole class use the same doc

    async def test_search_returns_results(self, httpx_client):
        resp = await httpx_client.post(
            "/api/search",
            json={"query": "Python programming language", "threshold": 0.1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) > 0
        # Each result should have the expected fields
        first = data["results"][0]
        assert "chunk_id" in first
        assert "content" in first
        assert "score" in first

    async def test_results_have_score_field(self, httpx_client):
        resp = await httpx_client.post(
            "/api/search",
            json={"query": "Guido van Rossum Python creator", "threshold": 0.1},
        )
        data = resp.json()
        for result in data["results"]:
            assert isinstance(result["score"], float)
            assert result["score"] >= 0

    async def test_top_k_respected(self, httpx_client):
        resp = await httpx_client.post(
            "/api/search",
            json={"query": "Python", "top_k": 1, "threshold": 0.1},
        )
        data = resp.json()
        assert len(data["results"]) <= 1

    async def test_high_threshold_fewer_results(self, httpx_client):
        resp = await httpx_client.post(
            "/api/search",
            json={"query": "completely unrelated quantum physics", "threshold": 0.95},
        )
        data = resp.json()
        # With a very high threshold, expect few or no results
        assert len(data["results"]) <= 2

    async def test_missing_query_422(self, httpx_client):
        resp = await httpx_client.post("/api/search", json={})
        assert resp.status_code == 422

    async def test_response_shape(self, httpx_client):
        resp = await httpx_client.post(
            "/api/search",
            json={"query": "Python", "threshold": 0.1},
        )
        data = resp.json()
        assert "results" in data
        assert "query" in data
        assert "total" in data


@pytest.fixture(scope="module", autouse=True)
async def _cleanup_search_doc(_search_doc_id):
    """Delete the test document after all search tests."""
    yield
    if "id" in _search_doc_id:
        import httpx as httpx_lib
        async with httpx_lib.AsyncClient(
            base_url="http://127.0.0.1:8000",
            headers={"X-API-Key": "dev-key-1"},
            timeout=10,
        ) as client:
            await client.delete(f"/api/documents/{_search_doc_id['id']}")
