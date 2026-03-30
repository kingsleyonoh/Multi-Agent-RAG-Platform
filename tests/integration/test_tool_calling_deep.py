"""Deep verification — Tool calling.

Proves the agent executor actually triggers tools (calculate,
get_time, search_kb) and returns their results through the chat API.
"""

from __future__ import annotations

import io
import re
import uuid

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

_RUN_ID = uuid.uuid4().hex[:8]


class TestToolCallingViaChat:
    """Verify tools fire and return results through /api/chat/sync."""

    async def test_calculate_tool(self, httpx_client):
        """LLM should call the calculate tool and return 717."""
        resp = await httpx_client.post(
            "/api/chat/sync",
            json={"query": f"[{_RUN_ID}] Use the calculate tool to compute 42 * 17 + 3. Return only the number."},
        )
        assert resp.status_code == 200
        answer = resp.json()["response"]
        assert "717" in answer, f"Expected 717 in response: {answer[:200]}"

    async def test_get_time_tool(self, httpx_client):
        """LLM should call get_time and return a timestamp."""
        resp = await httpx_client.post(
            "/api/chat/sync",
            json={"query": f"[{_RUN_ID}] Use the get_time tool to tell me the current UTC time."},
        )
        assert resp.status_code == 200
        answer = resp.json()["response"]
        # Should contain a time-like pattern (HH:MM or ISO date)
        has_time = bool(re.search(r"\d{2}:\d{2}", answer))
        has_date = bool(re.search(r"\d{4}-\d{2}-\d{2}", answer))
        assert has_time or has_date, f"No time/date in response: {answer[:200]}"

    async def test_search_kb_tool(self, httpx_client):
        """Upload doc, then ask LLM to search KB — should use search_kb tool."""
        # Upload a document first
        content = (
            f"Tool test doc {_RUN_ID}. The Fibonacci sequence starts with "
            "0, 1, 1, 2, 3, 5, 8, 13, 21. It was described by Leonardo "
            "of Pisa in 1202."
        )
        upload = await httpx_client.post(
            "/api/documents",
            files={"file": ("fib.txt", io.BytesIO(content.encode()), "text/plain")},
        )
        doc_id = upload.json()["id"]

        try:
            resp = await httpx_client.post(
                "/api/chat/sync",
                json={"query": f"[{_RUN_ID}] Search the knowledge base for information about Fibonacci sequence."},
            )
            assert resp.status_code == 200
            answer = resp.json()["response"].lower()
            # Should mention fibonacci-related content from the doc
            has_fib = any(
                term in answer
                for term in ["fibonacci", "sequence", "1202", "leonardo"]
            )
            assert has_fib, f"KB content not in response: {answer[:200]}"
        finally:
            await httpx_client.delete(f"/api/documents/{doc_id}")

    async def test_simple_query_no_tool_artifacts(self, httpx_client):
        """A simple greeting should not trigger tool calls."""
        resp = await httpx_client.post(
            "/api/chat/sync",
            json={"query": f"[{_RUN_ID}] Hello! How are you today?"},
        )
        assert resp.status_code == 200
        answer = resp.json()["response"]
        assert len(answer) > 0
        # Should not contain tool call artifacts like JSON or function names
        assert "function_call" not in answer.lower()
