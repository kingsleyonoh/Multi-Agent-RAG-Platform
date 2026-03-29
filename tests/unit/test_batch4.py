"""Tests for Batch 4: Vector search, OpenRouter client, and API routes."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Vector Search — dataclass and module-level tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSearchResult:
    """Tests for the SearchResult dataclass."""

    def test_search_result_creation(self) -> None:
        """SearchResult stores all fields correctly."""
        from src.retrieval.vector_search import SearchResult

        cid = uuid.uuid4()
        did = uuid.uuid4()
        r = SearchResult(
            chunk_id=cid,
            document_id=did,
            content="test content",
            score=0.85,
            document_title="Test Doc",
            document_source="upload",
        )
        assert r.chunk_id == cid
        assert r.score == 0.85
        assert r.content == "test content"

    def test_search_result_is_frozen(self) -> None:
        """SearchResult is immutable."""
        from src.retrieval.vector_search import SearchResult

        r = SearchResult(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            content="x",
            score=0.5,
            document_title="T",
            document_source="s",
        )
        with pytest.raises(AttributeError):
            r.score = 0.9  # type: ignore[misc]

    def test_search_function_exists(self) -> None:
        """The search function is importable and callable."""
        from src.retrieval.vector_search import search
        import asyncio

        assert callable(search)
        assert asyncio.iscoroutinefunction(search)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OpenRouter Client  (src/llm/openrouter.py)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class _FakeSettings:
    OPENROUTER_BASE_URL = "https://openrouter.test/api/v1"
    OPENROUTER_API_KEY = "sk-test-key"
    OPENROUTER_APP_NAME = "test-app"


class TestOpenRouterClient:
    """Tests for the OpenRouter chat completion client."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_completion(self) -> None:
        """Happy-path chat completion."""
        from src.llm.openrouter import chat_completion

        respx.post("https://openrouter.test/api/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "choices": [{"message": {"content": "Hello world"}}],
                    "model": "test-model",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                },
            )
        )

        result = await chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            model="test-model",
            settings=_FakeSettings(),
        )
        assert result.content == "Hello world"
        assert result.model_used == "test-model"
        assert result.tokens_in == 10
        assert result.tokens_out == 5

    @respx.mock
    @pytest.mark.asyncio
    async def test_rate_limit_raises(self) -> None:
        """429 → RuntimeError with RATE_LIMITED."""
        from src.llm.openrouter import chat_completion

        respx.post("https://openrouter.test/api/v1/chat/completions").mock(
            return_value=Response(429, json={"error": "rate limited"})
        )

        with pytest.raises(RuntimeError, match="RATE_LIMITED"):
            await chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                model="m",
                settings=_FakeSettings(),
            )

    @respx.mock
    @pytest.mark.asyncio
    async def test_server_error_raises(self) -> None:
        """5xx → RuntimeError with LLM_PROVIDER_ERROR."""
        from src.llm.openrouter import chat_completion

        respx.post("https://openrouter.test/api/v1/chat/completions").mock(
            return_value=Response(503, text="Service Unavailable")
        )

        with pytest.raises(RuntimeError, match="LLM_PROVIDER_ERROR"):
            await chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                model="m",
                settings=_FakeSettings(),
            )

    @respx.mock
    @pytest.mark.asyncio
    async def test_cost_limit_raises(self) -> None:
        """402 → RuntimeError with COST_LIMIT_EXCEEDED."""
        from src.llm.openrouter import chat_completion

        respx.post("https://openrouter.test/api/v1/chat/completions").mock(
            return_value=Response(402, json={"error": "insufficient credits"})
        )

        with pytest.raises(RuntimeError, match="COST_LIMIT_EXCEEDED"):
            await chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                model="m",
                settings=_FakeSettings(),
            )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Route: Documents  (src/api/routes/documents.py)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _mock_session():
    """Return a mock async DB session for testing routes."""
    session = AsyncMock()
    # Mock execute to return empty result set
    mock_result = MagicMock()
    mock_result.scalar.return_value = 0
    mock_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
    mock_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()
    return session


def _test_app():
    """Minimal app with dependency overrides for testing."""
    from src.api.dependencies import (
        get_cost_tracker,
        get_db_session,
        get_semantic_cache,
        get_settings_dep,
    )
    from src.api.middleware.auth import require_api_key
    from src.cache.semantic import SemanticCache
    from src.llm.cost_tracker import CostTracker
    from src.main import create_app

    app = create_app()

    # Override dependencies (lifespan doesn't run in test mode)
    app.dependency_overrides[get_db_session] = lambda: _mock_session()
    app.dependency_overrides[require_api_key] = lambda: {
        "api_key": "test-key",
        "user_id": "test-user",
    }
    app.dependency_overrides[get_cost_tracker] = lambda: CostTracker()
    app.dependency_overrides[get_semantic_cache] = lambda: SemanticCache()

    return app


class TestDocumentRoutes:
    """Tests for document API endpoints."""

    @pytest.mark.asyncio
    async def test_list_documents_empty(self) -> None:
        """GET /api/documents returns empty list."""
        transport = ASGITransport(app=_test_app())
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/documents")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    @pytest.mark.asyncio
    async def test_get_document_returns_404(self) -> None:
        """GET /api/documents/{id} returns 404 for missing doc."""
        doc_id = uuid.uuid4()
        transport = ASGITransport(app=_test_app())
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/documents/{doc_id}")
        assert resp.status_code == 404


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Route: Search  (src/api/routes/search.py)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSearchRoute:
    """Tests for the search API endpoint."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_search_returns_results(self) -> None:
        """POST /api/search with mocked embedder + search → 200."""
        respx.post("https://openrouter.ai/api/v1/embeddings").mock(
            return_value=Response(
                200,
                json={
                    "data": [{"embedding": [0.1] * 1536, "index": 0}],
                },
            )
        )

        app = _test_app()
        transport = ASGITransport(app=app)
        with patch(
            "src.api.routes.search.vector_search",
            new=AsyncMock(return_value=[]),
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/search",
                    json={"query": "test query"},
                )
        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body
        assert body["query"] == "test query"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Route: Chat  (src/api/routes/chat.py)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestChatRoute:
    """Tests for the chat API endpoint."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_sync_chat_returns_response(self) -> None:
        """POST /api/chat/sync with mocked LLM → valid response."""
        # Mock embedding
        respx.post("https://openrouter.ai/api/v1/embeddings").mock(
            return_value=Response(
                200,
                json={"data": [{"embedding": [0.1] * 1536, "index": 0}]},
            )
        )
        # Mock chat completion
        respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "choices": [{"message": {"content": "RAG retrieves context."}}],
                    "model": "openai/gpt-4o-mini",
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10},
                },
            )
        )

        app = _test_app()
        transport = ASGITransport(app=app)
        with patch(
            "src.api.routes.chat.vector_search",
            new=AsyncMock(return_value=[]),
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/chat/sync",
                    json={"query": "What is RAG?"},
                )
        assert resp.status_code == 200
        body = resp.json()
        assert "response" in body
        assert body["model_used"] is not None
