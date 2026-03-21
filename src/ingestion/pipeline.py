"""Document ingestion pipeline.

Orchestrates extract → hash → dedup → chunk → embed → store.

Usage::

    from src.ingestion.pipeline import ingest_document

    doc_id = await ingest_document(
        title="My Doc", source="upload",
        content=raw_text, metadata={},
        session=db_session, settings=app_settings,
    )
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chunk, Document
from src.ingestion.chunker import chunk_text
from src.ingestion.embedder import embed_texts
from src.lib.utils import content_hash

logger = structlog.get_logger(__name__)


async def ingest_document(
    *,
    title: str,
    source: str,
    content: str,
    metadata: dict,
    session: AsyncSession,
    settings: object,
) -> uuid.UUID:
    """Ingest a document: extract → dedup → chunk → embed → store.

    Args:
        title: Document title.
        source: Origin identifier (``"upload"``, ``"url"``, etc.).
        content: Raw text content (already extracted).
        metadata: Arbitrary metadata dict.
        session: SQLAlchemy async session.
        settings: Application settings with embedding config.

    Returns:
        The UUID of the new or existing document.

    Raises:
        ValueError: If *content* is empty.
        RuntimeError: If embedding fails.
    """
    if not content.strip():
        raise ValueError("EMPTY_DOCUMENT")

    # ── Dedup by content hash ──────────────────────────────────
    doc_hash = content_hash(content)
    stmt = select(Document).where(Document.content_hash == doc_hash)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is not None:
        logger.info("document_duplicate", hash=doc_hash[:12], existing_id=str(existing.id))
        return existing.id

    # ── Chunk ──────────────────────────────────────────────────
    chunks = chunk_text(
        content,
        chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
    )

    # ── Embed ──────────────────────────────────────────────────
    texts = [c.content for c in chunks]
    embeddings = await embed_texts(
        texts=texts,
        base_url=settings.OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY,
        model=settings.EMBEDDING_MODEL,
    )

    # ── Store ──────────────────────────────────────────────────
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        title=title,
        source=source,
        content=content,
        content_hash=doc_hash,
        doc_metadata=metadata,
        chunk_count=len(chunks),
        status="embedded",
    )
    session.add(doc)

    for chunk, embedding in zip(chunks, embeddings):
        session.add(
            Chunk(
                document_id=doc_id,
                chunk_index=chunk.index,
                content=chunk.content,
                token_count=chunk.token_count,
                embedding=embedding,
                doc_metadata=metadata,
            )
        )

    await session.flush()
    logger.info(
        "document_ingested",
        doc_id=str(doc_id),
        chunks=len(chunks),
        title=title[:50],
    )
    return doc_id
