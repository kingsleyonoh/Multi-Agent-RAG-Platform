"""Document API endpoints.

Provides CRUD operations for documents including file upload,
URL ingestion, listing with cursor pagination, and deletion.

Usage::

    from src.api.routes.documents import router
    app.include_router(router)
"""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


# ── Request / Response schemas ─────────────────────────────────


class UrlIngestRequest(BaseModel):
    """Body for URL-based ingestion."""

    url: str
    title: str | None = None
    metadata: dict = Field(default_factory=dict)


class DocumentResponse(BaseModel):
    """Single document response."""

    id: uuid.UUID
    title: str
    source: str
    status: str
    chunk_count: int
    content_hash: str
    metadata: dict
    created_at: str

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Paginated document list."""

    items: list[DocumentResponse]
    next_cursor: str | None = None
    total: int


# ── Endpoints ──────────────────────────────────────────────────


@router.post("", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Query(default=None),
) -> dict:
    """Upload a file for ingestion.

    The full pipeline (extract → chunk → embed → store) runs inline
    for MVP; background processing comes in Phase 2.
    """
    # Placeholder — full wiring requires DB session dependency
    content = await file.read()
    return {
        "message": "Document upload endpoint ready",
        "filename": file.filename,
        "size": len(content),
        "title": title or file.filename,
    }


@router.post("/url", status_code=201)
async def ingest_url(body: UrlIngestRequest) -> dict:
    """Ingest a document from a URL."""
    return {
        "message": "URL ingestion endpoint ready",
        "url": body.url,
        "title": body.title or body.url,
    }


@router.get("")
async def list_documents(
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
    status: Annotated[str | None, Query()] = None,
    source: Annotated[str | None, Query()] = None,
) -> dict:
    """List documents with cursor-based pagination."""
    from src.lib.pagination import clamp_limit

    actual_limit = clamp_limit(limit)
    return {
        "items": [],
        "next_cursor": None,
        "total": 0,
        "limit": actual_limit,
        "filters": {"status": status, "source": source},
    }


@router.get("/{doc_id}")
async def get_document(doc_id: uuid.UUID) -> dict:
    """Get a single document by ID."""
    return {
        "message": "Document detail endpoint ready",
        "id": str(doc_id),
    }


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: uuid.UUID) -> None:
    """Delete a document and its chunks."""
    logger.info("document_delete_requested", doc_id=str(doc_id))
    # Full DB wiring comes with session dependency injection
