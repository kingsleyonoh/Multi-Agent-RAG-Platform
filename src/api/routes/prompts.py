"""Prompt CRUD API endpoints — PostgreSQL-backed.

Exposes:
  - ``POST /api/prompts``       — create a prompt
  - ``GET  /api/prompts``       — list all prompts
  - ``PUT  /api/prompts/{id}``  — update a prompt (version auto-increments)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.db.models import Prompt

router = APIRouter(tags=["prompts"])


# ── request / response schemas ───────────────────────────────────────


class CreatePromptRequest(BaseModel):
    name: str
    template: str
    model_hint: str | None = None


class UpdatePromptRequest(BaseModel):
    template: str | None = None
    is_active: bool | None = None
    model_hint: str | None = None


# ── helpers ──────────────────────────────────────────────────────────


def _prompt_to_dict(p: Prompt) -> dict:
    """Serialise a Prompt ORM instance to a response dict."""
    return {
        "id": str(p.id),
        "name": p.name,
        "template": p.template,
        "version": p.version,
        "is_active": p.is_active,
        "model_hint": p.model_hint,
    }


# ── endpoints ────────────────────────────────────────────────────────


@router.post("", status_code=201)
async def create_prompt(
    body: CreatePromptRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new prompt template."""
    prompt = Prompt(
        name=body.name,
        template=body.template,
        model_hint=body.model_hint,
    )
    session.add(prompt)
    await session.commit()
    await session.refresh(prompt)
    return _prompt_to_dict(prompt)


@router.get("")
async def list_prompts(
    session: AsyncSession = Depends(get_db_session),
):
    """Return all prompts."""
    stmt = select(Prompt).order_by(Prompt.name)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [_prompt_to_dict(p) for p in rows]


@router.put("/{prompt_id}")
async def update_prompt(
    prompt_id: str,
    body: UpdatePromptRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Update a prompt — auto-increments version on template change."""
    try:
        prompt_uuid = uuid.UUID(prompt_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Prompt not found") from exc

    prompt = await session.get(Prompt, prompt_uuid)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if body.template is not None:
        prompt.template = body.template
        prompt.version += 1
    if body.is_active is not None:
        prompt.is_active = body.is_active
    if body.model_hint is not None:
        prompt.model_hint = body.model_hint

    await session.commit()
    await session.refresh(prompt)
    return _prompt_to_dict(prompt)
