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

# ── Module-level state (set by init_search_kb at startup) ────────

_session_factory = None
_settings = None


def init_search_kb(session_factory, settings) -> None:
    """Wire search_kb to real infrastructure.

    Called once at app startup from ``main.py`` lifespan.
    """
    global _session_factory, _settings
    _session_factory = session_factory
    _settings = settings
    logger.info("search_kb_initialized")


async def _do_search(query: str, top_k: int) -> list:
    """Execute vector search via embed + pgvector.

    Gracefully returns empty list when infrastructure is not wired.
    """
    if _session_factory is None or _settings is None:
        logger.debug("search_kb_not_wired")
        return []

    from src.ingestion.embedder import embed_texts
    from src.retrieval.vector_search import search

    embeddings = await embed_texts(
        texts=[query],
        base_url=_settings.OPENROUTER_BASE_URL,
        api_key=_settings.OPENROUTER_API_KEY,
        model=_settings.EMBEDDING_MODEL,
    )
    async with _session_factory() as session:
        return await search(
            session=session,
            query_embedding=embeddings[0],
            top_k=top_k,
            threshold=_settings.SIMILARITY_THRESHOLD,
        )


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
