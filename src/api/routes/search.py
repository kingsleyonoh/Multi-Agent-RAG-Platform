"""Search API endpoint.

Provides vector similarity search over ingested documents.

Usage::

    from src.api.routes.search import router
    app.include_router(router)
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session, get_settings_dep
from src.api.middleware.auth import require_api_key
from src.config import Settings
from src.ingestion.embedder import embed_texts
from src.retrieval.vector_search import search as vector_search

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
async def search_documents(
    body: SearchRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dep),
    auth: dict = Depends(require_api_key),
) -> SearchResponse:
    """Embed query and search via pgvector cosine similarity.

    Returns results ranked by relevance score.
    """
    logger.info("search_requested", query_len=len(body.query), top_k=body.top_k)

    # 1. Embed the query
    try:
        embeddings = await embed_texts(
            texts=[body.query],
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.EMBEDDING_MODEL,
        )
        query_embedding = embeddings[0]
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502, detail=f"Embedding failed: {exc}"
        ) from exc

    # 2. Vector search
    results = await vector_search(
        query_embedding=query_embedding,
        session=session,
        top_k=body.top_k,
        threshold=body.threshold,
        document_ids=body.document_ids,
    )

    items = [
        SearchResultItem(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            content=r.content,
            score=r.score,
            document_title=r.document_title,
            document_source=r.document_source,
        )
        for r in results
    ]

    return SearchResponse(
        results=items,
        query=body.query,
        total=len(items),
    )
