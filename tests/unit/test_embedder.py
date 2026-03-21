"""Unit tests for embedding generator (TDD)."""

from __future__ import annotations

import pytest
import httpx
import respx


class TestEmbedTexts:
    """Tests for src.ingestion.embedder.embed_texts (async, httpx mocked)."""

    @pytest.mark.asyncio
    async def test_returns_list_of_vectors(self, respx_mock) -> None:
        from src.ingestion.embedder import embed_texts

        mock_response = {
            "data": [
                {"embedding": [0.1] * 1536, "index": 0},
                {"embedding": [0.2] * 1536, "index": 1},
            ],
        }
        respx_mock.post("https://openrouter.ai/api/v1/embeddings").mock(
            return_value=httpx.Response(200, json=mock_response),
        )

        result = await embed_texts(
            texts=["hello", "world"],
            base_url="https://openrouter.ai/api/v1",
            api_key="test-key",
            model="openai/text-embedding-3-small",
        )
        assert len(result) == 2
        assert len(result[0]) == 1536

    @pytest.mark.asyncio
    async def test_api_error_raises(self, respx_mock) -> None:
        from src.ingestion.embedder import embed_texts

        respx_mock.post("https://openrouter.ai/api/v1/embeddings").mock(
            return_value=httpx.Response(500, json={"error": "Internal"}),
        )

        with pytest.raises(RuntimeError, match="(?i)embed|api|failed"):
            await embed_texts(
                texts=["hello"],
                base_url="https://openrouter.ai/api/v1",
                api_key="test-key",
                model="openai/text-embedding-3-small",
            )

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self, respx_mock) -> None:
        from src.ingestion.embedder import embed_texts

        result = await embed_texts(
            texts=[],
            base_url="https://openrouter.ai/api/v1",
            api_key="test-key",
            model="openai/text-embedding-3-small",
        )
        assert result == []
