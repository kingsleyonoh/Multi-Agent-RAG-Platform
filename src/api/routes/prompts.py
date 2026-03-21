"""Prompt CRUD API endpoints.

Exposes:
  - ``POST /api/prompts``       — create a prompt
  - ``GET  /api/prompts``       — list all prompts
  - ``PUT  /api/prompts/{id}``  — update a prompt (version auto-increments)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.prompts.registry import PromptRegistry

router = APIRouter(tags=["prompts"])

# Module-level registry (replaced in production by a singleton).
_registry = PromptRegistry()


# ── request / response schemas ───────────────────────────────────────

class CreatePromptRequest(BaseModel):
    name: str
    template: str
    model_hint: str | None = None


class UpdatePromptRequest(BaseModel):
    template: str | None = None
    is_active: bool | None = None
    model_hint: str | None = None


# ── endpoints ────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_prompt(body: CreatePromptRequest):
    """Create a new prompt template."""
    return _registry.create(
        name=body.name,
        template=body.template,
        model_hint=body.model_hint,
    )


@router.get("")
async def list_prompts():
    """Return all prompts."""
    return _registry.list_all()


@router.put("/{prompt_id}")
async def update_prompt(prompt_id: str, body: UpdatePromptRequest):
    """Update a prompt — auto-increments version on template change."""
    result = _registry.update(
        prompt_id,
        template=body.template,
        is_active=body.is_active,
        model_hint=body.model_hint,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return result
