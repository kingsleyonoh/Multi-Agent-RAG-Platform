"""Chat API route.

Provides synchronous and streaming chat completion with RAG context retrieval.

Usage::

    from src.api.routes.chat import router
    app.include_router(router)
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    get_cost_tracker,
    get_db_session,
    get_settings_dep,
)
from src.api.middleware.auth import require_api_key
from src.config import Settings
from src.guardrails.pipeline import run_input_guardrails, run_output_guardrails
from src.ingestion.embedder import embed_texts
from src.llm.openrouter import chat_completion
from src.llm.streaming import format_sse, stream_chat_completion
from src.retrieval.vector_search import search as vector_search

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


# ── Helpers ────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Use the following retrieved context "
    "to answer the user's question. If the context is relevant, cite it. "
    "If you don't know the answer from the context, say so.\n\n"
    "Context:\n{context}"
)


def _build_context(chunks: list) -> str:
    """Format retrieved chunks into a context block."""
    if not chunks:
        return "No relevant documents found."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[{i}] {chunk.content[:500]}")
    return "\n\n".join(parts)


# ── Endpoints ──────────────────────────────────────────────────


@router.post("/sync")
async def sync_chat(
    body: ChatRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dep),
    auth: dict = Depends(require_api_key),
    cost_tracker=Depends(get_cost_tracker),
) -> ChatResponse:
    """Query → retrieve context → LLM call → response.

    Full pipeline: guardrails → embed query → vector search →
    build prompt → chat completion → output guardrails.
    """
    logger.info("chat_sync_requested", query_len=len(body.query), model=body.model)

    # 1. Input guardrails
    guard_result = run_input_guardrails(
        body.query,
        denied_topics=[],
        injection_threshold=settings.GUARDRAIL_INJECTION_THRESHOLD,
        pii_mode=settings.GUARDRAIL_PII_MODE,
    )
    if not guard_result.passed:
        flags_detail = "; ".join(f.detail for f in guard_result.flags)
        raise HTTPException(status_code=400, detail=f"Blocked: {flags_detail}")

    # 2. Embed query + search
    sources: list[ChatSource] = []
    context_str = "No relevant documents found."
    search_results = []

    try:
        embeddings = await embed_texts(
            texts=[body.query],
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.EMBEDDING_MODEL,
        )
        search_results = await vector_search(
            query_embedding=embeddings[0],
            session=session,
            top_k=body.top_k,
            threshold=settings.SIMILARITY_THRESHOLD,
        )
        context_str = _build_context(search_results)
        sources = [
            ChatSource(
                document_title=r.document_title,
                content=r.content[:200],
                score=r.score,
            )
            for r in search_results
        ]
    except RuntimeError:
        logger.warning("search_failed_fallback", query=body.query[:50])

    # 3. LLM call
    model = body.model or settings.DEFAULT_MODEL
    system_prompt = _SYSTEM_PROMPT.format(context=context_str)

    try:
        result = await chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": body.query},
            ],
            model=model,
            settings=settings,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # 4. Output guardrails (informational — don't block)
    source_chunks = [r.content for r in search_results]
    source_ids = [r.document_title for r in search_results]
    out_guard = run_output_guardrails(result.content, source_chunks, source_ids)
    if out_guard.flags:
        logger.info(
            "output_guardrail_flags",
            count=len(out_guard.flags),
            types=[f.type for f in out_guard.flags],
        )

    # 5. Track cost
    cost_tracker.record_cost(
        model=result.model_used,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        cost_usd=result.cost_usd,
        user_id=auth["user_id"],
    )

    return ChatResponse(
        response=result.content,
        sources=sources,
        model_used=result.model_used,
        cost=result.cost_usd,
    )


@router.post("")
async def streaming_chat(
    body: ChatRequest,
    settings: Settings = Depends(get_settings_dep),
    auth: dict = Depends(require_api_key),
) -> StreamingResponse:
    """SSE streaming chat endpoint.

    Streams token-by-token responses as Server-Sent Events.
    """
    logger.info("chat_stream_requested", query_len=len(body.query), model=body.model)

    async def _event_generator():
        async for event in stream_chat_completion(
            messages=[{"role": "user", "content": body.query}],
            model=body.model or settings.DEFAULT_MODEL,
            settings=settings,
        ):
            yield format_sse(event)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
    )
