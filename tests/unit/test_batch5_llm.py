"""Tests for Batch 5: Model router, SSE streaming, cost tracker."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Shared test settings
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class _FakeSettings:
    OPENROUTER_BASE_URL = "https://openrouter.test/api/v1"
    OPENROUTER_API_KEY = "sk-test-key"
    OPENROUTER_APP_NAME = "test-app"
    DEFAULT_MODEL = "openai/gpt-4o-mini"
    DAILY_COST_LIMIT_USD = 10.0
    MAX_TOOL_CALLS_PER_TURN = 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Model Router  (src/llm/router.py)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestModelRouter:
    """Tests for multi-model routing logic."""

    def test_routing_table_exists(self) -> None:
        """ROUTING_TABLE maps task types to model IDs."""
        from src.llm.router import ROUTING_TABLE

        assert isinstance(ROUTING_TABLE, dict)
        assert "chat" in ROUTING_TABLE
        assert "summarization" in ROUTING_TABLE
        assert "embedding" in ROUTING_TABLE

    def test_route_model_returns_default_for_chat(self) -> None:
        """Chat tasks route to DEFAULT_MODEL."""
        from src.llm.router import route_model

        model = route_model(task_type="chat", settings=_FakeSettings())
        assert model == "openai/gpt-4o-mini"

    def test_route_model_preferred_bypasses_table(self) -> None:
        """When preferred_model is set, it overrides the routing table."""
        from src.llm.router import route_model

        model = route_model(
            task_type="chat",
            settings=_FakeSettings(),
            preferred_model="anthropic/claude-3-haiku",
        )
        assert model == "anthropic/claude-3-haiku"

    def test_route_model_unknown_task_falls_back(self) -> None:
        """Unknown task type falls back to DEFAULT_MODEL."""
        from src.llm.router import route_model

        model = route_model(task_type="unknown_task", settings=_FakeSettings())
        assert model == "openai/gpt-4o-mini"

    @respx.mock
    @pytest.mark.asyncio
    async def test_routed_chat_uses_correct_model(self) -> None:
        """routed_chat_completion resolves model via router then calls LLM."""
        from src.llm.router import routed_chat_completion

        respx.post("https://openrouter.test/api/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "choices": [{"message": {"content": "routed response"}}],
                    "model": "openai/gpt-4o-mini",
                    "usage": {"prompt_tokens": 5, "completion_tokens": 3},
                },
            )
        )

        result = await routed_chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            task_type="chat",
            settings=_FakeSettings(),
        )
        assert result.content == "routed response"
        assert result.model_used == "openai/gpt-4o-mini"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SSE Streaming  (src/llm/streaming.py)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSSEStreaming:
    """Tests for SSE streaming wrapper."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_yields_tokens(self) -> None:
        """stream_chat_completion yields SSE events with token data."""
        from src.llm.streaming import stream_chat_completion

        # Simulate OpenRouter streaming response (SSE format)
        sse_body = (
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
            "data: [DONE]\n\n"
        )
        respx.post("https://openrouter.test/api/v1/chat/completions").mock(
            return_value=Response(200, text=sse_body)
        )

        tokens = []
        async for event in stream_chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            model="openai/gpt-4o-mini",
            settings=_FakeSettings(),
        ):
            if event.get("done"):
                break
            tokens.append(event["token"])

        assert tokens == ["Hello", " world"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_handles_api_error(self) -> None:
        """API error during streaming yields error event."""
        from src.llm.streaming import stream_chat_completion

        respx.post("https://openrouter.test/api/v1/chat/completions").mock(
            return_value=Response(500, text="Server Error")
        )

        events = []
        async for event in stream_chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            model="openai/gpt-4o-mini",
            settings=_FakeSettings(),
        ):
            events.append(event)

        assert len(events) == 1
        assert "error" in events[0]

    def test_format_sse_event(self) -> None:
        """format_sse produces valid SSE text."""
        from src.llm.streaming import format_sse

        result = format_sse({"token": "hi", "done": False})
        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        payload = json.loads(result.removeprefix("data: ").strip())
        assert payload["token"] == "hi"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cost Tracker  (src/llm/cost_tracker.py)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCostTracker:
    """Tests for per-request cost tracking."""

    def test_cost_record_creation(self) -> None:
        """CostRecord stores all fields correctly."""
        from src.llm.cost_tracker import CostRecord

        r = CostRecord(
            model="openai/gpt-4o-mini",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.001,
            user_id="user-1",
        )
        assert r.model == "openai/gpt-4o-mini"
        assert r.cost_usd == 0.001
        assert r.user_id == "user-1"

    def test_record_cost_stores_entry(self) -> None:
        """record_cost adds record to the tracker store."""
        from src.llm.cost_tracker import CostTracker

        tracker = CostTracker()
        tracker.record_cost(
            model="openai/gpt-4o-mini",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.005,
            user_id="user-1",
        )
        assert tracker.get_user_daily_cost("user-1") == pytest.approx(0.005)

    def test_daily_cost_aggregation(self) -> None:
        """Multiple records aggregate into daily total."""
        from src.llm.cost_tracker import CostTracker

        tracker = CostTracker()
        for _ in range(3):
            tracker.record_cost(
                model="m",
                tokens_in=10,
                tokens_out=5,
                cost_usd=0.01,
                user_id="user-1",
            )
        assert tracker.get_user_daily_cost("user-1") == pytest.approx(0.03)

    def test_check_budget_under_limit(self) -> None:
        """check_budget returns True when under daily limit."""
        from src.llm.cost_tracker import CostTracker

        tracker = CostTracker()
        tracker.record_cost(
            model="m", tokens_in=10, tokens_out=5, cost_usd=1.0, user_id="u1"
        )
        assert tracker.check_budget("u1", daily_limit=10.0) is True

    def test_check_budget_over_limit(self) -> None:
        """check_budget returns False when over daily limit."""
        from src.llm.cost_tracker import CostTracker

        tracker = CostTracker()
        tracker.record_cost(
            model="m", tokens_in=10, tokens_out=5, cost_usd=11.0, user_id="u1"
        )
        assert tracker.check_budget("u1", daily_limit=10.0) is False

    def test_separate_users_tracked_independently(self) -> None:
        """Different user IDs have independent cost tracking."""
        from src.llm.cost_tracker import CostTracker

        tracker = CostTracker()
        tracker.record_cost(
            model="m", tokens_in=10, tokens_out=5, cost_usd=5.0, user_id="a"
        )
        tracker.record_cost(
            model="m", tokens_in=10, tokens_out=5, cost_usd=3.0, user_id="b"
        )
        assert tracker.get_user_daily_cost("a") == pytest.approx(5.0)
        assert tracker.get_user_daily_cost("b") == pytest.approx(3.0)

    def test_unknown_user_returns_zero_cost(self) -> None:
        """Unknown user ID returns 0.0 daily cost."""
        from src.llm.cost_tracker import CostTracker

        tracker = CostTracker()
        assert tracker.get_user_daily_cost("nobody") == 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Streaming Chat Endpoint  (POST /api/chat)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _test_app():
    """Minimal app for endpoint testing."""
    from src.api.dependencies import get_cost_tracker, get_db_session, get_semantic_cache
    from src.api.middleware.auth import require_api_key
    from src.cache.semantic import SemanticCache
    from src.llm.cost_tracker import CostTracker
    from src.main import create_app

    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: {
        "api_key": "test-key",
        "user_id": "test-user",
    }
    app.dependency_overrides[get_cost_tracker] = lambda: CostTracker()
    app.dependency_overrides[get_semantic_cache] = lambda: SemanticCache()
    return app


class TestStreamingChatEndpoint:
    """Tests for the SSE streaming chat endpoint."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_streaming_endpoint_exists(self) -> None:
        """POST /api/chat returns a streaming response."""
        # Mock the streaming LLM call
        sse_body = (
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
            "data: [DONE]\n\n"
        )
        respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=Response(200, text=sse_body)
        )

        transport = ASGITransport(app=_test_app())
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/chat",
                json={"query": "What is RAG?"},
            )
        # Should return 200 with text/event-stream content type
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
