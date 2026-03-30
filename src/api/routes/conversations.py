"""Conversation CRUD API routes — PostgreSQL-backed.

Provides endpoints for managing conversations and messages:
- POST   /api/conversations            → create conversation
- GET    /api/conversations             → list user conversations
- GET    /api/conversations/:id         → get conversation with messages
- DELETE /api/conversations/:id         → delete conversation
- POST   /api/conversations/:id/messages → add message to conversation

Usage::

    from src.api.routes.conversations import router
    app.include_router(router)
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.dependencies import get_db_session
from src.db.models import Conversation, Message

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ── Schemas ─────────────────────────────────────────────────────────


class CreateConversationRequest(BaseModel):
    """Request body for creating a conversation."""

    user_id: str
    title: str | None = None
    model_preference: str | None = None


class ConversationResponse(BaseModel):
    """Response body for a conversation."""

    id: str
    user_id: str
    title: str | None
    model_preference: str | None
    total_tokens: int
    total_cost_usd: float
    created_at: str
    updated_at: str


class AddMessageRequest(BaseModel):
    """Request body for adding a message."""

    role: str
    content: str
    model_used: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None


class MessageResponse(BaseModel):
    """Response body for a message."""

    id: str
    conversation_id: str
    role: str
    content: str
    model_used: str | None
    tokens_in: int | None
    tokens_out: int | None
    created_at: str


# ── Helpers ────────────────────────────────────────────────────────


def _conv_to_dict(conv: Conversation) -> dict:
    """Serialise a Conversation ORM instance to a response dict."""
    return {
        "id": str(conv.id),
        "user_id": conv.user_id,
        "title": conv.title,
        "model_preference": conv.model_preference,
        "total_tokens": conv.total_tokens,
        "total_cost_usd": float(conv.total_cost_usd),
        "created_at": str(conv.created_at),
        "updated_at": str(conv.updated_at),
    }


def _msg_to_dict(msg: Message) -> dict:
    """Serialise a Message ORM instance to a response dict."""
    return {
        "id": str(msg.id),
        "conversation_id": str(msg.conversation_id),
        "role": msg.role,
        "content": msg.content,
        "model_used": msg.model_used,
        "tokens_in": msg.tokens_in,
        "tokens_out": msg.tokens_out,
        "created_at": str(msg.created_at),
    }


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("", status_code=201)
async def create_conversation(
    body: CreateConversationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Create a new conversation.

    Returns the created conversation with an assigned ID.
    """
    conv = Conversation(
        user_id=body.user_id,
        title=body.title,
        model_preference=body.model_preference,
    )
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    logger.info("conversation_created", id=str(conv.id), user_id=body.user_id)
    return _conv_to_dict(conv)


@router.get("")
async def list_conversations(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    """List conversations for a user.

    Args:
        user_id: Filter conversations by user ID.

    Returns:
        List of conversation dicts.
    """
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [_conv_to_dict(c) for c in rows]


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get a conversation with its messages.

    Args:
        conversation_id: UUID of the conversation.

    Returns:
        Conversation dict with ``messages`` list.

    Raises:
        HTTPException: 404 if conversation not found.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc

    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conv_uuid)
    )
    result = await session.execute(stmt)
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    data = _conv_to_dict(conv)
    data["messages"] = [_msg_to_dict(m) for m in conv.messages]
    return data


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a conversation and its messages.

    Args:
        conversation_id: UUID of the conversation.

    Raises:
        HTTPException: 404 if conversation not found.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc

    conv = await session.get(Conversation, conv_uuid)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await session.delete(conv)
    await session.commit()
    logger.info("conversation_deleted", id=conversation_id)


@router.post("/{conversation_id}/messages", status_code=201)
async def add_message(
    conversation_id: str,
    body: AddMessageRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Add a message to a conversation.

    Args:
        conversation_id: UUID of the conversation.
        body: Message data.

    Returns:
        Created message dict.

    Raises:
        HTTPException: 404 if conversation not found.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc

    conv = await session.get(Conversation, conv_uuid)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg = Message(
        conversation_id=conv_uuid,
        role=body.role,
        content=body.content,
        model_used=body.model_used,
        tokens_in=body.tokens_in,
        tokens_out=body.tokens_out,
    )
    session.add(msg)

    # Update conversation stats
    if body.tokens_in:
        conv.total_tokens += body.tokens_in
    if body.tokens_out:
        conv.total_tokens += body.tokens_out

    await session.commit()
    await session.refresh(msg)

    logger.info("message_added", conversation_id=conversation_id, role=body.role)
    return _msg_to_dict(msg)
