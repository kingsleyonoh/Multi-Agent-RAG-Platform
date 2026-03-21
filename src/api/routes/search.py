"""Search API endpoint.

Provides vector similarity search over ingested documents.

Usage::

    from src.api.routes.search import router
    app.include_router(router)
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["search"])


# ── Schemas ────────────────────────────────────────────────────


class SearchRequest(BaseModel):
    """Search query payload."""

    query: str
    top_k: int = Field(default=10, ge=1, le=50)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    document_ids: list[uuid.UUID] | None = None
    metadata: dict | None = None


class SearchResultItem(BaseModel):
    """A single search result."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    score: float
    document_title: str
    document_source: str


class SearchResponse(BaseModel):
    """Search response with results and metadata."""

    results: list[SearchResultItem]
    query: str
    total: int


# ── Endpoint ───────────────────────────────────────────────────


@router.post("/search")
async def search_documents(body: SearchRequest) -> SearchResponse:
    """Embed query and search via pgvector cosine similarity.

    Returns results ranked by relevance score.
    """
    # Placeholder — full wiring requires DB session + embedder dependency
    logger.info("search_requested", query_len=len(body.query), top_k=body.top_k)
    return SearchResponse(
        results=[],
        query=body.query,
        total=0,
    )
