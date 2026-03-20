"""Shared utility functions for the Multi-Agent RAG Platform.

Provides content hashing for document deduplication (PRD §4.1),
timezone-aware timestamp generation, and text truncation helpers.

Usage::

    from src.lib.utils import content_hash, utc_now, truncate_text

    hash_val = content_hash(document_text)     # SHA-256 hex digest
    now = utc_now()                             # datetime with UTC tz
    short = truncate_text(long_text, max_len=100)
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone


def content_hash(text: str) -> str:
    """Return the SHA-256 hex digest of *text* for deduplication.

    Line endings are normalised (``\\r\\n`` → ``\\n``) before hashing
    so the same document produces the same hash regardless of platform.

    Args:
        text: The document content to hash.

    Returns:
        A 64-character lowercase hexadecimal string.
    """
    normalised = text.replace("\r\n", "\n")
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime.

    All timestamps in the platform MUST use this helper instead of
    ``datetime.utcnow()`` (which returns a naïve datetime) or
    ``datetime.now()`` (which uses local time).

    Returns:
        ``datetime`` with ``tzinfo=timezone.utc``.
    """
    return datetime.now(timezone.utc)


def truncate_text(text: str, *, max_len: int = 200) -> str:
    """Truncate *text* to *max_len* characters, appending ``...``.

    If *text* is already within *max_len*, it is returned unchanged.
    Useful for log messages, error summaries, and preview fields.

    Args:
        text: The string to truncate.
        max_len: Maximum allowed length (default ``200``).

    Returns:
        The original string if short enough, otherwise truncated with
        a trailing ``...`` so the total length equals *max_len*.
    """
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
