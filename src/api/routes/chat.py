"""Chat API route — full RAG pipeline.

Provides synchronous and streaming chat completion with:
- Input/output guardrails
- Semantic cache interception
- Memory manager (multi-turn history)
- Hybrid retrieval (vector + keyword + graph)
- Agent executor (ReAct tool calling)
- Model routing
- Background evaluation
- Cost tracking

Usage::

    from src.api.routes.chat import router
    app.include_router(router)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.agents.executor import AgentExecutor
from src.agents.registry import ToolRegistry, ToolSpec
from src.agents.tools.calculate import (
    TOOL_DESCRIPTION as calc_desc,
    TOOL_NAME as calc_name,
    TOOL_PARAMETERS as calc_params,
    calculate,
)
from src.agents.tools.get_time import (
    TOOL_DESCRIPTION as gt_desc,
    TOOL_NAME as gt_name,
    TOOL_PARAMETERS as gt_params,
    get_time,
)
from src.agents.tools.query_graph import (
    TOOL_DESCRIPTION as qg_desc,
    TOOL_NAME as qg_name,
    TOOL_PARAMETERS as qg_params,
    query_graph,
)
from src.agents.tools.search_kb import (
    TOOL_DESCRIPTION as sk_desc,
    TOOL_NAME as sk_name,
    TOOL_PARAMETERS as sk_params,
    search_kb,
)
from src.agents.tools.summarize import (
    TOOL_DESCRIPTION as sum_desc,
    TOOL_NAME as sum_name,
    TOOL_PARAMETERS as sum_params,
    summarize,
)
from src.api.dependencies import (
    get_cost_tracker,
    get_db_session,
    get_semantic_cache,
    get_settings_dep,
)
from src.api.middleware.auth import require_api_key
from src.config import Settings
from src.db.models import Conversation, Evaluation, Message
from src.evaluation.harness import EvaluationHarness
from src.guardrails.pipeline import run_input_guardrails, run_output_guardrails
from src.ingestion.embedder import embed_texts
from src.llm.router import route_model
from src.llm.streaming import format_sse, stream_chat_completion
from src.memory.manager import MemoryManager
from src.retrieval.engine import HybridRetrievalEngine

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ── Schemas ────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Chat request payload (sync and streaming)."""

    query: str
    conversation_id: str | None = None
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
    conversation_id: str | None = None
    evaluation: dict | None = None


# ── Helpers ────────────────────────────────────────────────────


_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Use the following retrieved context "
    "to answer the user's question. If the context is relevant, cite it. "
    "If you don't know the answer from the context, say so.\n\n"
    "Context:\n{context}"
)

_MEMORY_PROMPT = (
    "\n\nConversation summary:\n{summary}"
    "\n\nKnown entities:\n{entities}"
)


def _build_context(chunks: list) -> str:
    """Format retrieved chunks into a context block."""
    if not chunks:
        return "No relevant documents found."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        text = getattr(chunk, "text", getattr(chunk, "content", str(chunk)))
        parts.append(f"[{i}] {text[:500]}")
    return "\n\n".join(parts)


@dataclass
class PipelineContext:
    """Pre-LLM pipeline context shared between sync and streaming."""

    system_prompt: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    sources: list[ChatSource] = field(default_factory=list)
    source_chunks: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    model: str = ""
    query_embedding: list[float] = field(default_factory=list)
    conversation_id: str | None = None
    cached_response: str | None = None


async def _prepare_chat_context(
    *,
    body: ChatRequest,
    session: AsyncSession,
    settings: Settings,
    cache: object,
) -> PipelineContext:
    """Execute all pre-LLM pipeline steps.

    1. Input guardrails
    2. Semantic cache check
    3. Model routing
    4. Embed query + hybrid retrieval
    5. Memory context (if conversation_id provided)
    6. Build system prompt

    Returns:
        PipelineContext with prepared messages and metadata.
    """
    ctx = PipelineContext()

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

    # 2. Semantic cache check
    if cache is not None:
        hit = await cache.lookup(body.query)
        if hit is not None:
            logger.info("cache_hit", similarity=hit.get("similarity"))
            ctx.cached_response = hit["response"]
            return ctx

    # 3. Model routing
    ctx.model = route_model(
        task_type="chat",
        settings=settings,
        preferred_model=body.model,
    )

    # 4. Embed query + retrieval
    context_str = "No relevant documents found."
    try:
        embeddings = await embed_texts(
            texts=[body.query],
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.EMBEDDING_MODEL,
        )
        ctx.query_embedding = embeddings[0]

        engine = HybridRetrievalEngine(
            session=session, settings=settings,
        )
        retrieval_results = await engine.retrieve(
            query=body.query,
            query_embedding=ctx.query_embedding,
            top_n=body.top_k,
        )

        context_str = _build_context(retrieval_results)
        ctx.sources = [
            ChatSource(
                document_title=getattr(r, "source_metadata", {}).get(
                    "title", f"chunk-{r.chunk_id}",
                ),
                content=r.text[:200],
                score=r.score,
            )
            for r in retrieval_results
        ]
        ctx.source_chunks = [r.text for r in retrieval_results]
        ctx.source_ids = [r.chunk_id for r in retrieval_results]
    except RuntimeError:
        logger.warning("search_failed_fallback", query=body.query[:50])

    # 5. Memory context
    memory_addition = ""
    if body.conversation_id:
        ctx.conversation_id = body.conversation_id
        try:
            conv_uuid = uuid.UUID(body.conversation_id)
            stmt = (
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .where(Conversation.id == conv_uuid)
            )
            result = await session.execute(stmt)
            conv = result.scalar_one_or_none()
            if conv and conv.messages:
                mm = MemoryManager(window_size=20)
                mem_ctx = await mm.build_context(conv.messages)

                # Add recent messages to the message list
                for msg in mem_ctx.context_messages:
                    role = getattr(msg, "role", "user")
                    content = getattr(msg, "content", str(msg))
                    ctx.messages.append({"role": role, "content": content})

                if mem_ctx.entity_context:
                    memory_addition += f"\n\n{mem_ctx.entity_context}"
                if mem_ctx.memory_summary:
                    memory_addition += (
                        f"\n\nPrior conversation summary: "
                        f"{mem_ctx.memory_summary}"
                    )
        except Exception:
            logger.warning("memory_load_failed", exc_info=True)

    # 6. Build system prompt + messages
    ctx.system_prompt = _SYSTEM_PROMPT.format(context=context_str)
    if memory_addition:
        ctx.system_prompt += memory_addition

    # Prepend system, then history, then current user message
    full_messages = [{"role": "system", "content": ctx.system_prompt}]
    full_messages.extend(ctx.messages)
    full_messages.append({"role": "user", "content": body.query})
    ctx.messages = full_messages

    return ctx


async def _run_evaluation(
    *,
    query: str,
    response_text: str,
    chunks: list[str],
    message_id: str | None,
    session_factory,
    db_engine,
) -> None:
    """Background task: run evaluation and persist results."""


    harness = EvaluationHarness()
    scores = harness.evaluate(query=query, response=response_text, chunks=chunks)

    if message_id and db_engine:
        try:
            from src.db.postgres import get_session_factory

            factory = get_session_factory(db_engine)
            async with factory() as bg_session:
                msg_uuid = uuid.UUID(message_id)
                for metric, score in scores.items():
                    if metric in ("flagged",):
                        continue
                    eval_row = Evaluation(
                        message_id=msg_uuid,
                        metric=metric,
                        score=round(score, 4),
                        details={"source": "auto"},
                    )
                    bg_session.add(eval_row)
                await bg_session.commit()
        except Exception:
            logger.warning("evaluation_persist_failed", exc_info=True)


# ── Endpoints ──────────────────────────────────────────────────


@router.post("/sync")
async def sync_chat(
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dep),
    auth: dict = Depends(require_api_key),
    cost_tracker=Depends(get_cost_tracker),
    cache=Depends(get_semantic_cache),
) -> ChatResponse:
    """Query → guardrails → cache → retrieve → agent → evaluate.

    Full pipeline: guardrails → semantic cache → embed query →
    hybrid retrieval → memory → agent executor → output guardrails →
    evaluation → cost tracking.
    """
    logger.info("chat_sync_requested", query_len=len(body.query), model=body.model)

    # Pre-LLM pipeline
    ctx = await _prepare_chat_context(
        body=body, session=session, settings=settings, cache=cache,
    )

    # Cache hit → short-circuit
    if ctx.cached_response:
        return ChatResponse(
            response=ctx.cached_response,
            sources=[],
            model_used="cache",
            cost=0.0,
            conversation_id=ctx.conversation_id,
        )

    # Agent executor with tool calling
    try:
        registry = ToolRegistry()
        _all_tools = [
            (calc_name, calc_desc, calc_params, calculate),
            (sk_name, sk_desc, sk_params, search_kb),
            (qg_name, qg_desc, qg_params, query_graph),
            (sum_name, sum_desc, sum_params, summarize),
            (gt_name, gt_desc, gt_params, get_time),
        ]
        for t_name, t_desc, t_params, t_handler in _all_tools:
            registry.register(
                ToolSpec(
                    name=t_name,
                    description=t_desc,
                    parameters=t_params,
                    handler=t_handler,
                ),
            )

        executor = AgentExecutor(
            registry=registry, settings=settings, max_steps=settings.MAX_TOOL_CALLS_PER_TURN,
        )
        exec_result = await executor.run(
            user_message=body.query,
            system_prompt=ctx.system_prompt,
            model=ctx.model,
        )
        response_text = exec_result.answer
        model_used = exec_result.model_used
        tokens_in = exec_result.tokens_in
        tokens_out = exec_result.tokens_out
        cost_usd = exec_result.cost_usd
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Output guardrails (informational — don't block)
    out_guard = run_output_guardrails(
        response_text, ctx.source_chunks, ctx.source_ids,
    )
    if out_guard.flags:
        logger.info(
            "output_guardrail_flags",
            count=len(out_guard.flags),
            types=[f.type for f in out_guard.flags],
        )

    # Cost tracking
    cost_tracker.record_cost(
        model=model_used,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        user_id=auth["user_id"],
    )

    # Persist messages to conversation (if conversation_id provided)
    msg_id = None
    if body.conversation_id:
        try:
            conv_uuid = uuid.UUID(body.conversation_id)
            user_msg = Message(
                conversation_id=conv_uuid,
                role="user",
                content=body.query,
            )
            assistant_msg = Message(
                conversation_id=conv_uuid,
                role="assistant",
                content=response_text,
                model_used=model_used,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                sources={"chunks": ctx.source_ids},
            )
            session.add(user_msg)
            session.add(assistant_msg)
            await session.commit()
            await session.refresh(assistant_msg)
            msg_id = str(assistant_msg.id)
        except Exception:
            logger.warning("message_persist_failed", exc_info=True)

    # Background: cache store + evaluation
    if cache is not None and ctx.query_embedding:
        background_tasks.add_task(
            cache.store, body.query, response_text, ctx.query_embedding,
        )

    db_engine = getattr(request.app.state, "db_engine", None)
    background_tasks.add_task(
        _run_evaluation,
        query=body.query,
        response_text=response_text,
        chunks=ctx.source_chunks,
        message_id=msg_id,
        session_factory=None,
        db_engine=db_engine,
    )

    return ChatResponse(
        response=response_text,
        sources=ctx.sources,
        model_used=model_used,
        cost=cost_usd,
        conversation_id=body.conversation_id,
    )


@router.post("")
async def streaming_chat(
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dep),
    auth: dict = Depends(require_api_key),
    cache=Depends(get_semantic_cache),
) -> StreamingResponse:
    """SSE streaming chat endpoint with full pipeline.

    Pre-LLM pipeline (guardrails, cache, retrieval, memory) runs
    before the stream starts. Streams token-by-token as SSE.
    """
    logger.info("chat_stream_requested", query_len=len(body.query), model=body.model)

    # Pre-LLM pipeline
    ctx = await _prepare_chat_context(
        body=body, session=session, settings=settings, cache=cache,
    )

    # Cache hit → return as single SSE event
    if ctx.cached_response:
        async def _cached_stream():
            yield format_sse({"type": "content", "text": ctx.cached_response})
            yield format_sse({"type": "done"})
        return StreamingResponse(
            _cached_stream(), media_type="text/event-stream",
        )

    async def _event_generator():
        async for event in stream_chat_completion(
            messages=ctx.messages,
            model=ctx.model,
            settings=settings,
        ):
            yield format_sse(event)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
    )
