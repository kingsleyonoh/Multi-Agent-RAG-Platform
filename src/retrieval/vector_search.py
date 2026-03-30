"""Vector search via pgvector cosine similarity.

Usage::

    from src.retrieval.vector_search import search

    results = await search(
        query_embedding=[0.1, ...],
        session=db_session,
        top_k=10,
        threshold=0.7,
    )
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Sequence

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chunk, Document

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A single search result with relevance metadata."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    score: float
    document_title: str
    document_source: str


async def search(
    *,
    query_embedding: list[float],
    session: AsyncSession,
    top_k: int = 10,
    threshold: float = 0.7,
    document_ids: list[uuid.UUID] | None = None,
) -> list[SearchResult]:
    """Run a cosine similarity search against chunk embeddings.

    Args:
        query_embedding: The 1536-dim query vector.
        session: SQLAlchemy async session.
        top_k: Maximum number of results.
        threshold: Minimum similarity score (0-1).
        document_ids: Optional filter to specific documents.

    Returns:
        List of :class:`SearchResult` ordered by descending similarity.
    """
    # Build cosine similarity expression
    from sqlalchemy import literal_column
    embedding_literal = str(query_embedding)
    similarity_expr = literal_column(
        f"1 - (chunks.embedding <=> '{embedding_literal}')"
    )

    stmt = (
        select(
            Chunk.id,
            Chunk.document_id,
            Chunk.content,
            similarity_expr.label("score"),
            Document.title,
            Document.source,
        )
        .join(Document, Chunk.document_id == Document.id)
        .where(text(f"1 - (chunks.embedding <=> '{embedding_literal}') >= {threshold}"))
        .order_by(text(f"chunks.embedding <=> '{embedding_literal}'"))
        .limit(top_k)
    )

    if document_ids:
        stmt = stmt.where(Chunk.document_id.in_(document_ids))

    result = await session.execute(stmt)
    rows = result.all()

    return [
        SearchResult(
            chunk_id=row[0],
            document_id=row[1],
            content=row[2],
            score=float(row[3]),
            document_title=row[4],
            document_source=row[5],
        )
        for row in rows
    ]
