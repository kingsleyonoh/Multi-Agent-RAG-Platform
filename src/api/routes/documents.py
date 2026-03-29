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
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session, get_settings_dep
from src.api.middleware.auth import require_api_key
from src.config import Settings
from src.db.models import Document
from src.ingestion.pipeline import ingest_document

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


# ── Helpers ────────────────────────────────────────────────────


def _detect_extractor(filename: str):
    """Return the correct extractor based on file extension."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return "pdf"
    if name.endswith(".md"):
        return "markdown"
    return "text"


async def _extract_content(file_bytes: bytes, filename: str) -> str:
    """Extract text content from uploaded file bytes."""
    ext_type = _detect_extractor(filename)

    if ext_type == "pdf":
        from src.ingestion.extractors.pdf import extract
        return extract(file_bytes)
    if ext_type == "markdown":
        from src.ingestion.extractors.markdown import extract
        return extract(file_bytes.decode("utf-8", errors="replace"))

    from src.ingestion.extractors.text import extract
    return extract(file_bytes.decode("utf-8", errors="replace"))


# ── Endpoints ──────────────────────────────────────────────────


@router.post("", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dep),
    auth: dict = Depends(require_api_key),
) -> dict:
    """Upload a file for ingestion.

    The full pipeline (extract → chunk → embed → store) runs inline.
    """
    content_bytes = await file.read()
    filename = file.filename or "untitled.txt"

    try:
        text_content = await _extract_content(content_bytes, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        doc_id = await ingest_document(
            title=title or filename,
            source="upload",
            content=text_content,
            metadata={"filename": filename, "user_id": auth["user_id"]},
            session=session,
            settings=settings,
        )
        await session.commit()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info("document_uploaded", doc_id=str(doc_id), filename=filename)
    return {
        "id": str(doc_id),
        "title": title or filename,
        "filename": filename,
        "size": len(content_bytes),
        "status": "embedded",
    }


@router.post("/url", status_code=201)
async def ingest_url(
    body: UrlIngestRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dep),
    auth: dict = Depends(require_api_key),
) -> dict:
    """Ingest a document from a URL."""
    from src.ingestion.extractors.url import extract

    try:
        text_content = await extract(body.url)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Failed to extract from URL: {exc}"
        ) from exc

    try:
        doc_id = await ingest_document(
            title=body.title or body.url,
            source="url",
            content=text_content,
            metadata={**body.metadata, "url": body.url, "user_id": auth["user_id"]},
            session=session,
            settings=settings,
        )
        await session.commit()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "id": str(doc_id),
        "title": body.title or body.url,
        "source": "url",
        "status": "embedded",
    }


@router.get("")
async def list_documents(
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
    status: Annotated[str | None, Query()] = None,
    source: Annotated[str | None, Query()] = None,
    session: AsyncSession = Depends(get_db_session),
    auth: dict = Depends(require_api_key),
) -> dict:
    """List documents with cursor-based pagination."""
    from src.lib.pagination import clamp_limit

    actual_limit = clamp_limit(limit)

    # Count total
    count_stmt = select(func.count()).select_from(Document)
    if status:
        count_stmt = count_stmt.where(Document.status == status)
    if source:
        count_stmt = count_stmt.where(Document.source == source)
    total = (await session.execute(count_stmt)).scalar() or 0

    # Fetch documents
    stmt = select(Document).order_by(Document.created_at.desc()).limit(actual_limit)
    if status:
        stmt = stmt.where(Document.status == status)
    if source:
        stmt = stmt.where(Document.source == source)
    if cursor:
        try:
            cursor_id = uuid.UUID(cursor)
            stmt = stmt.where(Document.id < cursor_id)
        except ValueError:
            pass

    result = await session.execute(stmt)
    docs = result.scalars().all()

    items = [
        {
            "id": str(d.id),
            "title": d.title,
            "source": d.source,
            "status": d.status,
            "chunk_count": d.chunk_count,
            "content_hash": d.content_hash,
            "metadata": d.doc_metadata or {},
            "created_at": str(d.created_at),
        }
        for d in docs
    ]

    next_cursor = str(docs[-1].id) if len(docs) == actual_limit else None

    return {
        "items": items,
        "next_cursor": next_cursor,
        "total": total,
    }


@router.get("/{doc_id}")
async def get_document(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    auth: dict = Depends(require_api_key),
) -> dict:
    """Get a single document by ID."""
    result = await session.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": str(doc.id),
        "title": doc.title,
        "source": doc.source,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "content_hash": doc.content_hash,
        "metadata": doc.doc_metadata or {},
        "created_at": str(doc.created_at),
    }


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    auth: dict = Depends(require_api_key),
) -> None:
    """Delete a document and its chunks."""
    result = await session.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await session.delete(doc)
    await session.commit()
    logger.info("document_deleted", doc_id=str(doc_id))
