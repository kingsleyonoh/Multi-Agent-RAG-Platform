"""Cursor-based pagination utility.

Provides encoding/decoding of opaque cursors (base64-encoded UUIDs)
and limit clamping for consistent pagination across all list endpoints.

Usage::

    from src.lib.pagination import encode_cursor, decode_cursor, clamp_limit

    cursor = encode_cursor(last_id)
    uid = decode_cursor(cursor_string)
    limit = clamp_limit(user_limit)
"""

from __future__ import annotations

import base64
import uuid


_DEFAULT_LIMIT = 25
_MAX_LIMIT = 100


def encode_cursor(uid: uuid.UUID) -> str:
    """Encode a UUID into an opaque cursor string."""
    return base64.urlsafe_b64encode(uid.bytes).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> uuid.UUID:
    """Decode an opaque cursor string back to a UUID.

    Raises:
        ValueError: If the cursor is malformed.
    """
    try:
        # Re-add padding
        padded = cursor + "=" * (4 - len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded)
        return uuid.UUID(bytes=raw)
    except Exception as exc:
        raise ValueError(f"Invalid cursor: {cursor}") from exc


def clamp_limit(limit: int | None, *, default: int = _DEFAULT_LIMIT, maximum: int = _MAX_LIMIT) -> int:
    """Clamp *limit* to [1, *maximum*], returning *default* if None/invalid."""
    if limit is None or limit <= 0:
        return default
    return min(limit, maximum)
