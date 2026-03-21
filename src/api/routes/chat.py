"""Chat API route.

Provides synchronous chat completion with RAG context retrieval.

Usage::

    from src.api.routes.chat import router
    app.include_router(router)
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ── Schemas ────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Sync chat request payload."""

    query: str
    model: str | None = None
    top_k: int = Field(default=10, ge=1, le=50)


class ChatSource(BaseModel):
    """A source chunk used for context."""

    document_title: str
    content: str
    score: float


class ChatResponse(BaseModel):
    """Chat response with sources and metadata."""

    response: str
    sources: list[ChatSource]
    model_used: str
    cost: float


# ── Endpoint ───────────────────────────────────────────────────


@router.post("/sync")
async def sync_chat(body: ChatRequest) -> ChatResponse:
    """Query → retrieve context → LLM call → response.

    Full pipeline: embed query → vector search → build prompt → chat completion.
    """
    # Placeholder — full wiring requires DB session + embedder + LLM deps
    logger.info("chat_sync_requested", query_len=len(body.query), model=body.model)
    return ChatResponse(
        response="Chat endpoint ready — awaiting full pipeline wiring.",
        sources=[],
        model_used=body.model or "openai/gpt-4o-mini",
        cost=0.0,
    )
