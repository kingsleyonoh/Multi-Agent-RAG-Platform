"""Recursive character text chunker.

Splits text into chunks of approximately ``chunk_size`` characters
with ``overlap`` characters shared between adjacent chunks.  Splits
on paragraph breaks, then newlines, then sentences, then spaces.

Usage::

    from src.ingestion.chunker import chunk_text

    chunks = chunk_text(text, chunk_size=512, overlap=50)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkResult:
    """A single chunk produced by :func:`chunk_text`."""

    content: str
    index: int
    token_count: int


_SEPARATORS = ["\n\n", "\n", ". ", " "]


def _approx_token_count(text: str) -> int:
    """Rough token estimate: ~4 chars per token (GPT-family heuristic)."""
    return max(1, len(text) // 4)


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Recursively split *text* into pieces of ≤ *chunk_size* chars."""
    if len(text) <= chunk_size:
        return [text]

    # Find the best separator that produces a split
    for sep in _SEPARATORS:
        parts = text.split(sep)
        if len(parts) > 1:
            break
    else:
        # No separator found — hard split
        parts = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]
        return parts

    # Merge parts into chunks of <= chunk_size
    chunks: list[str] = []
    current = parts[0]
    for part in parts[1:]:
        candidate = current + sep + part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current)
            # Overlap: keep some trailing content
            if overlap > 0 and len(current) > overlap:
                current = current[-overlap:] + sep + part
            else:
                current = part
    if current:
        chunks.append(current)

    return chunks


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50,
) -> list[ChunkResult]:
    """Split *text* into overlapping chunks.

    Args:
        text: The full document text.
        chunk_size: Target maximum characters per chunk.
        overlap: Number of characters to overlap between chunks.

    Returns:
        List of :class:`ChunkResult` in order.

    Raises:
        ValueError: If *text* is empty.
    """
    if not text.strip():
        raise ValueError("EMPTY_DOCUMENT")

    raw_chunks = _split_text(text.strip(), chunk_size, overlap)
    return [
        ChunkResult(
            content=c,
            index=i,
            token_count=_approx_token_count(c),
        )
        for i, c in enumerate(raw_chunks)
        if c.strip()  # skip empty chunks
    ]
