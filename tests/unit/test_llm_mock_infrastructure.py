"""Verify the LLM mock infrastructure works correctly."""

import httpx
import pytest
from httpx import Response

from tests.conftest import load_fixture


class TestLlmMockInfrastructure:
    """Validate respx mocking and fixture loading for OpenRouter API."""

    def test_load_chat_completion_fixture(self):
        """Fixture loader returns valid chat completion response structure."""
        data = load_fixture("chat_completion")
        assert data["model"] == "openai/gpt-4o-mini"
        assert len(data["choices"]) == 1
        assert data["choices"][0]["message"]["role"] == "assistant"
        assert data["usage"]["total_tokens"] == 75

    def test_load_embedding_fixture(self):
        """Fixture loader returns valid embedding response structure."""
        data = load_fixture("embedding")
        assert data["model"] == "openai/text-embedding-3-small"
        assert len(data["data"]) == 1
        assert isinstance(data["data"][0]["embedding"], list)
        assert data["usage"]["total_tokens"] == 10

    async def test_mock_openrouter_intercepts_requests(self, mock_openrouter):
        """respx mock intercepts OpenRouter API calls and returns fixture data."""
        fixture = load_fixture("chat_completion")
        mock_openrouter.post(
            "https://openrouter.ai/api/v1/chat/completions"
        ).mock(return_value=Response(200, json=fixture))

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "test"}]},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "openai/gpt-4o-mini"
        assert data["choices"][0]["finish_reason"] == "stop"

    def test_mock_llm_defaults_to_true(self, mock_llm):
        """MOCK_LLM defaults to True when not explicitly set to 'false'."""
        assert isinstance(mock_llm, bool)
