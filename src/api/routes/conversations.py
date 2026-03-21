"""Conversation CRUD API routes.

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
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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


# ── In-memory store (swap to DB in wiring phase) ───────────────────


_conversations: dict[str, dict] = {}
_messages: dict[str, list[dict]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("", status_code=201)
async def create_conversation(body: CreateConversationRequest) -> dict:
    """Create a new conversation.

    Returns the created conversation with an assigned ID.
    """
    conv_id = str(uuid.uuid4())
    now = _now_iso()
    conv = {
        "id": conv_id,
        "user_id": body.user_id,
        "title": body.title,
        "model_preference": body.model_preference,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "created_at": now,
        "updated_at": now,
    }
    _conversations[conv_id] = conv
    _messages[conv_id] = []
    logger.info("conversation_created", id=conv_id, user_id=body.user_id)
    return conv


@router.get("")
async def list_conversations(user_id: str) -> list[dict]:
    """List conversations for a user.

    Args:
        user_id: Filter conversations by user ID.

    Returns:
        List of conversation dicts.
    """
    return [
        c for c in _conversations.values()
        if c["user_id"] == user_id
    ]


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict:
    """Get a conversation with its messages.

    Args:
        conversation_id: UUID of the conversation.

    Returns:
        Conversation dict with ``messages`` list.

    Raises:
        HTTPException: 404 if conversation not found.
    """
    conv = _conversations.get(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {**conv, "messages": _messages.get(conversation_id, [])}


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str) -> None:
    """Delete a conversation and its messages.

    Args:
        conversation_id: UUID of the conversation.

    Raises:
        HTTPException: 404 if conversation not found.
    """
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    del _conversations[conversation_id]
    _messages.pop(conversation_id, None)
    logger.info("conversation_deleted", id=conversation_id)


@router.post("/{conversation_id}/messages", status_code=201)
async def add_message(conversation_id: str, body: AddMessageRequest) -> dict:
    """Add a message to a conversation.

    Args:
        conversation_id: UUID of the conversation.
        body: Message data.

    Returns:
        Created message dict.

    Raises:
        HTTPException: 404 if conversation not found.
    """
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_id = str(uuid.uuid4())
    msg = {
        "id": msg_id,
        "conversation_id": conversation_id,
        "role": body.role,
        "content": body.content,
        "model_used": body.model_used,
        "tokens_in": body.tokens_in,
        "tokens_out": body.tokens_out,
        "created_at": _now_iso(),
    }
    _messages[conversation_id].append(msg)

    # Update conversation stats
    conv = _conversations[conversation_id]
    if body.tokens_in:
        conv["total_tokens"] += body.tokens_in
    if body.tokens_out:
        conv["total_tokens"] += body.tokens_out
    conv["updated_at"] = _now_iso()

    logger.info("message_added", conversation_id=conversation_id, role=body.role)
    return msg
