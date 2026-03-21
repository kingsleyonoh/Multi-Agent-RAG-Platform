"""Chat API route.

Provides synchronous and streaming chat completion with RAG context retrieval.

Usage::

    from src.api.routes.chat import router
    app.include_router(router)
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.llm.streaming import format_sse, stream_chat_completion

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


@router.post("")
async def streaming_chat(body: ChatRequest) -> StreamingResponse:
    """SSE streaming chat endpoint.

    Streams token-by-token responses as Server-Sent Events.
    """
    logger.info("chat_stream_requested", query_len=len(body.query), model=body.model)

    # Inline settings for now — will be replaced by DI
    class _InlineSettings:
        OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
        OPENROUTER_API_KEY = "placeholder"
        OPENROUTER_APP_NAME = "multi-agent-rag-platform"

    async def _event_generator():
        async for event in stream_chat_completion(
            messages=[{"role": "user", "content": body.query}],
            model=body.model or "openai/gpt-4o-mini",
            settings=_InlineSettings(),
        ):
            yield format_sse(event)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
    )

