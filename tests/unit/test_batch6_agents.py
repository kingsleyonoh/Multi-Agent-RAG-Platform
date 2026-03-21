"""Tests for Batch 6: Tool registry and agent tools."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tool Registry  (src/agents/registry.py)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestToolSpec:
    """Tests for the ToolSpec dataclass."""

    def test_toolspec_creation(self) -> None:
        """ToolSpec stores name, description, parameters, handler."""
        from src.agents.registry import ToolSpec

        async def _handler(**kwargs):
            return "ok"

        spec = ToolSpec(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            handler=_handler,
        )
        assert spec.name == "test_tool"
        assert spec.description == "A test tool"
        assert callable(spec.handler)


class TestToolRegistry:
    """Tests for the ToolRegistry."""

    def test_register_and_get(self) -> None:
        """Registered tool can be retrieved by name."""
        from src.agents.registry import ToolRegistry, ToolSpec

        registry = ToolRegistry()

        async def _handler(**kwargs):
            return "result"

        spec = ToolSpec(
            name="my_tool",
            description="desc",
            parameters={},
            handler=_handler,
        )
        registry.register(spec)
        assert registry.get("my_tool") is spec

    def test_get_unknown_returns_none(self) -> None:
        """Getting unknown tool returns None."""
        from src.agents.registry import ToolRegistry

        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_list_tools(self) -> None:
        """list_tools returns all registered tool names."""
        from src.agents.registry import ToolRegistry, ToolSpec

        registry = ToolRegistry()

        for name in ["a", "b", "c"]:
            registry.register(
                ToolSpec(name=name, description=name, parameters={}, handler=AsyncMock())
            )
        names = registry.list_tools()
        assert set(names) == {"a", "b", "c"}

    def test_is_whitelisted(self) -> None:
        """Only registered tools are whitelisted."""
        from src.agents.registry import ToolRegistry, ToolSpec

        registry = ToolRegistry()
        registry.register(
            ToolSpec(name="allowed", description="ok", parameters={}, handler=AsyncMock())
        )
        assert registry.is_whitelisted("allowed") is True
        assert registry.is_whitelisted("forbidden") is False

    def test_duplicate_registration_overwrites(self) -> None:
        """Re-registering same name overwrites the tool."""
        from src.agents.registry import ToolRegistry, ToolSpec

        registry = ToolRegistry()
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        registry.register(
            ToolSpec(name="t", description="v1", parameters={}, handler=handler1)
        )
        registry.register(
            ToolSpec(name="t", description="v2", parameters={}, handler=handler2)
        )
        assert registry.get("t").description == "v2"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent Tool: search_kb
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSearchKBTool:
    """Tests for the knowledge base search tool."""

    @pytest.mark.asyncio
    async def test_search_kb_returns_results(self) -> None:
        """search_kb returns list of results from vector search."""
        from src.agents.tools.search_kb import search_kb

        # Mock the vector search dependency
        mock_result = MagicMock()
        mock_result.content = "test content"
        mock_result.score = 0.9
        mock_result.document_title = "Doc"
        mock_result.chunk_id = uuid.uuid4()

        with patch(
            "src.agents.tools.search_kb._do_search",
            new_callable=AsyncMock,
            return_value=[mock_result],
        ):
            result = await search_kb(query="what is RAG?", top_k=5)

        assert len(result) == 1
        assert result[0]["content"] == "test content"
        assert result[0]["score"] == 0.9

    @pytest.mark.asyncio
    async def test_search_kb_empty(self) -> None:
        """search_kb returns empty list when no results."""
        from src.agents.tools.search_kb import search_kb

        with patch(
            "src.agents.tools.search_kb._do_search",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await search_kb(query="xyz", top_k=5)

        assert result == []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent Tool: query_graph
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestQueryGraphTool:
    """Tests for the Neo4j graph query tool."""

    @pytest.mark.asyncio
    async def test_query_graph_read_only(self) -> None:
        """query_graph rejects write queries (CREATE, DELETE, SET, MERGE)."""
        from src.agents.tools.query_graph import query_graph

        for bad_query in [
            "CREATE (n:Node {name: 'x'})",
            "MATCH (n) DELETE n",
            "MATCH (n) SET n.x = 1",
            "MERGE (n:Node {id: 1})",
        ]:
            with pytest.raises(ValueError, match="read-only"):
                await query_graph(cypher=bad_query)

    @pytest.mark.asyncio
    async def test_query_graph_allows_match(self) -> None:
        """query_graph allows MATCH queries."""
        from src.agents.tools.query_graph import query_graph

        with patch(
            "src.agents.tools.query_graph._execute_cypher",
            new_callable=AsyncMock,
            return_value=[{"name": "Entity1"}],
        ):
            result = await query_graph(cypher="MATCH (n:Entity) RETURN n.name LIMIT 5")

        assert len(result) == 1
        assert result[0]["name"] == "Entity1"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent Tool: calculate
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCalculateTool:
    """Tests for the safe math evaluator."""

    @pytest.mark.asyncio
    async def test_basic_arithmetic(self) -> None:
        """calculate evaluates basic expressions."""
        from src.agents.tools.calculate import calculate

        assert await calculate(expression="2 + 3") == 5
        assert await calculate(expression="10 * 5") == 50
        assert await calculate(expression="100 / 4") == 25.0

    @pytest.mark.asyncio
    async def test_rejects_code_injection(self) -> None:
        """calculate blocks dangerous expressions."""
        from src.agents.tools.calculate import calculate

        for malicious in [
            "__import__('os').system('ls')",
            "exec('print(1)')",
            "eval('1+1')",
            "open('/etc/passwd')",
        ]:
            with pytest.raises(ValueError, match="[Uu]nsafe"):
                await calculate(expression=malicious)

    @pytest.mark.asyncio
    async def test_handles_invalid_expression(self) -> None:
        """calculate raises on unparseable input."""
        from src.agents.tools.calculate import calculate

        with pytest.raises(ValueError):
            await calculate(expression="not a math expression")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent Tool: get_time
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestGetTimeTool:
    """Tests for the current time tool."""

    @pytest.mark.asyncio
    async def test_returns_iso_format(self) -> None:
        """get_time returns ISO-8601 UTC timestamp."""
        from src.agents.tools.get_time import get_time
        from datetime import datetime, timezone

        result = await get_time()
        # Must parse without error
        dt = datetime.fromisoformat(result)
        assert dt.tzinfo is not None

    @pytest.mark.asyncio
    async def test_returns_string(self) -> None:
        """get_time returns a string."""
        from src.agents.tools.get_time import get_time

        result = await get_time()
        assert isinstance(result, str)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent Tool: summarize
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSummarizeTool:
    """Tests for the document summarization tool."""

    @pytest.mark.asyncio
    async def test_summarize_calls_llm(self) -> None:
        """summarize sends content to LLM and returns summary."""
        from src.agents.tools.summarize import summarize

        with patch(
            "src.agents.tools.summarize._call_llm",
            new_callable=AsyncMock,
            return_value="This document discusses RAG pipelines.",
        ):
            result = await summarize(content="Long document about RAG...")

        assert "RAG" in result

    @pytest.mark.asyncio
    async def test_summarize_handles_empty_content(self) -> None:
        """summarize returns message for empty content."""
        from src.agents.tools.summarize import summarize

        result = await summarize(content="")
        assert "empty" in result.lower() or "no content" in result.lower()
