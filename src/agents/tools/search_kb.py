"""Knowledge base search tool for agents.

Wraps the vector search module as an agent-callable tool.

Usage::

    from src.agents.tools.search_kb import search_kb
    results = await search_kb(query="what is RAG?", top_k=5)
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def _do_search(query: str, top_k: int) -> list:
    """Execute vector search. Separated for testability.

    In production, this calls the full embedding + search pipeline.
    """
    # Placeholder — requires DB session and embedder wiring
    return []


async def search_kb(*, query: str, top_k: int = 10) -> list[dict[str, Any]]:
    """Search the knowledge base for relevant chunks.

    Args:
        query: Natural language search query.
        top_k: Maximum number of results.

    Returns:
        List of dicts with ``content``, ``score``, ``document_title``, ``chunk_id``.
    """
    logger.info("search_kb_called", query_len=len(query), top_k=top_k)

    results = await _do_search(query, top_k)
    return [
        {
            "content": r.content,
            "score": r.score,
            "document_title": r.document_title,
            "chunk_id": str(r.chunk_id),
        }
        for r in results
    ]


# Tool metadata for registry
TOOL_NAME = "search_kb"
TOOL_DESCRIPTION = "Search the knowledge base for relevant document chunks."
TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query"},
        "top_k": {"type": "integer", "description": "Max results", "default": 10},
    },
    "required": ["query"],
}
