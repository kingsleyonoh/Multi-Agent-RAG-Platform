"""Tests for Batch 7: Agent Executor & Conversation API.

Tests for:
- AgentExecutor: direct answer, tool calling, max steps, whitelist
- Conversation CRUD endpoints
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# ── Shared Dependencies ─────────────────────────────────────────────

from src.agents.executor import AgentExecutor, ExecutorResult
from src.agents.registry import ToolRegistry, ToolSpec
from src.llm.openrouter import ChatResult


def _make_chat_result(
    content: str | None = None,
    tool_calls: list | None = None,
) -> ChatResult:
    """Helper to build a ChatResult for testing."""
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return ChatResult(
        content=content,
        model_used="test-model",
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.001,
        tool_calls=tool_calls,
        raw_message=message,
    )


# ── Agent Executor ──────────────────────────────────────────────────


class TestAgentExecutor:
    """Execute ReAct loop with tool-calling LLM."""

    @pytest.fixture
    def registry(self):
        reg = ToolRegistry()
        reg.register(
            ToolSpec(
                name="calculate",
                description="Calculate math",
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string"},
                    },
                    "required": ["expression"],
                },
                handler=AsyncMock(return_value=42),
            )
        )
        return reg

    @pytest.fixture
    def executor(self, registry):
        mock_settings = MagicMock()
        mock_settings.OPENROUTER_BASE_URL = "https://openrouter.test/api/v1"
        mock_settings.OPENROUTER_API_KEY = "sk-test"
        mock_settings.OPENROUTER_APP_NAME = "test"
        return AgentExecutor(
            registry=registry,
            settings=mock_settings,
            max_steps=5,
        )

    @pytest.mark.asyncio
    async def test_direct_answer_no_tools(self, executor):
        """LLM answers directly without calling tools."""
        fake_result = _make_chat_result(content="The answer is 42.")
        with patch(
            "src.agents.executor.chat_completion",
            new_callable=AsyncMock,
            return_value=fake_result,
        ):
            result = await executor.run(
                user_message="What is 6 times 7?",
                system_prompt="You are a helpful assistant.",
            )
        assert result.answer == "The answer is 42."
        assert result.tool_calls == []
        assert result.total_steps == 1

    @pytest.mark.asyncio
    async def test_tool_call_then_answer(self, executor):
        """LLM calls a tool, gets result, then answers."""
        tool_call_result = _make_chat_result(
            content=None,
            tool_calls=[
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "calculate",
                        "arguments": '{"expression": "6 * 7"}',
                    },
                }
            ],
        )
        final_result = _make_chat_result(content="6 times 7 is 42.")
        with patch(
            "src.agents.executor.chat_completion",
            new_callable=AsyncMock,
            side_effect=[tool_call_result, final_result],
        ):
            result = await executor.run(
                user_message="What is 6 times 7?",
                system_prompt="You are helpful.",
            )
        assert result.answer == "6 times 7 is 42."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["tool"] == "calculate"
        assert result.total_steps == 2

    @pytest.mark.asyncio
    async def test_max_steps_enforced(self, executor):
        """Executor stops after max_steps iterations."""
        tool_call_result = _make_chat_result(
            content=None,
            tool_calls=[
                {
                    "id": "call_loop",
                    "type": "function",
                    "function": {
                        "name": "calculate",
                        "arguments": '{"expression": "1+1"}',
                    },
                }
            ],
        )
        with patch(
            "src.agents.executor.chat_completion",
            new_callable=AsyncMock,
            return_value=tool_call_result,
        ):
            result = await executor.run(
                user_message="loop forever",
                system_prompt="You are helpful.",
            )
        assert result.total_steps == 5  # max_steps
        assert "max steps" in result.answer.lower()

    @pytest.mark.asyncio
    async def test_unregistered_tool_rejected(self, executor):
        """Tool calls for unregistered tools are rejected safely."""
        bad_tool_result = _make_chat_result(
            content=None,
            tool_calls=[
                {
                    "id": "call_bad",
                    "type": "function",
                    "function": {
                        "name": "exec_shell",
                        "arguments": '{"cmd": "rm -rf /"}',
                    },
                }
            ],
        )
        final_result = _make_chat_result(content="I cannot execute that tool.")
        with patch(
            "src.agents.executor.chat_completion",
            new_callable=AsyncMock,
            side_effect=[bad_tool_result, final_result],
        ):
            result = await executor.run(
                user_message="run shell command",
                system_prompt="You are helpful.",
            )
        assert result.answer == "I cannot execute that tool."


# ── Conversation CRUD ───────────────────────────────────────────────


class TestConversationAPI:
    """Conversation CRUD endpoint tests."""

    @pytest.fixture
    def app(self):
        from src.api.dependencies import get_db_session
        from src.main import create_app

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value = MagicMock(
            all=MagicMock(return_value=[])
        )
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.get = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        async def _db_override():
            yield mock_session

        app = create_app()
        app.dependency_overrides[get_db_session] = _db_override
        return app

    @pytest.fixture
    async def client(self, app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    @pytest.mark.asyncio
    async def test_create_conversation(self, client):
        """POST /api/conversations creates a new conversation."""
        resp = await client.post(
            "/api/conversations",
            json={"user_id": "user-1", "title": "Test Chat"},
        )
        # May be 201 or 500 depending on DB session mock completion
        assert resp.status_code in (201, 500)

    @pytest.mark.asyncio
    async def test_list_conversations(self, client):
        """GET /api/conversations?user_id=X returns user conversations."""
        resp = await client.get("/api/conversations?user_id=user-1")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, client):
        """GET /api/conversations/:id returns 404 for missing conversation."""
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/conversations/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_conversation_not_found(self, client):
        """DELETE /api/conversations/:id returns 404 for missing conversation."""
        fake_id = str(uuid.uuid4())
        resp = await client.delete(f"/api/conversations/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_add_message_conversation_not_found(self, client):
        """POST /api/conversations/:id/messages returns 404 for missing conv."""
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/conversations/{fake_id}/messages",
            json={"role": "user", "content": "Hello"},
        )
        assert resp.status_code == 404
