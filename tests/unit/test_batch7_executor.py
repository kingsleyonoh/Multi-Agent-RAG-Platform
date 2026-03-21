"""Tests for Batch 7: Agent executor (ReAct loop) + Conversation CRUD API."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.agents.executor import AgentExecutor, ExecutorResult
from src.agents.registry import ToolRegistry, ToolSpec


# ── Agent Executor ──────────────────────────────────────────────────


class TestExecutorResult:
    """ExecutorResult data class tests."""

    def test_result_creation(self):
        result = ExecutorResult(
            answer="Hello",
            tool_calls=[{"tool": "search_kb", "args": {"query": "test"}}],
            total_steps=2,
        )
        assert result.answer == "Hello"
        assert len(result.tool_calls) == 1
        assert result.total_steps == 2

    def test_result_defaults(self):
        result = ExecutorResult(answer="Done")
        assert result.tool_calls == []
        assert result.total_steps == 0


class TestAgentExecutor:
    """ReAct loop executor tests."""

    @pytest.fixture
    def registry(self):
        """Build a registry with one mock tool."""
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
        return AgentExecutor(
            registry=registry,
            max_steps=5,
        )

    @pytest.mark.asyncio
    async def test_direct_answer_no_tools(self, executor):
        """LLM answers directly without calling tools."""
        fake_response = {
            "choices": [
                {
                    "message": {
                        "content": "The answer is 42.",
                        "tool_calls": None,
                    }
                }
            ],
        }
        with patch(
            "src.agents.executor.chat_completion",
            new_callable=AsyncMock,
            return_value=fake_response,
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
        # First response: LLM wants to call calculate
        tool_call_response = {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "calculate",
                                    "arguments": '{"expression": "6 * 7"}',
                                },
                            }
                        ],
                    }
                }
            ],
        }
        # Second response: LLM answers with tool result
        final_response = {
            "choices": [
                {
                    "message": {
                        "content": "6 times 7 is 42.",
                        "tool_calls": None,
                    }
                }
            ],
        }
        with patch(
            "src.agents.executor.chat_completion",
            new_callable=AsyncMock,
            side_effect=[tool_call_response, final_response],
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
        # Always return a tool call — should stop after max_steps
        tool_call_response = {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_loop",
                                "type": "function",
                                "function": {
                                    "name": "calculate",
                                    "arguments": '{"expression": "1+1"}',
                                },
                            }
                        ],
                    }
                }
            ],
        }
        with patch(
            "src.agents.executor.chat_completion",
            new_callable=AsyncMock,
            return_value=tool_call_response,
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
        tool_call_response = {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_bad",
                                "type": "function",
                                "function": {
                                    "name": "exec_shell",
                                    "arguments": '{"cmd": "rm -rf /"}',
                                },
                            }
                        ],
                    }
                }
            ],
        }
        final_response = {
            "choices": [
                {
                    "message": {
                        "content": "I cannot execute that tool.",
                        "tool_calls": None,
                    }
                }
            ],
        }
        with patch(
            "src.agents.executor.chat_completion",
            new_callable=AsyncMock,
            side_effect=[tool_call_response, final_response],
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
        from src.main import create_app

        return create_app()

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
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] == "user-1"
        assert data["title"] == "Test Chat"
        assert "id" in data

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
