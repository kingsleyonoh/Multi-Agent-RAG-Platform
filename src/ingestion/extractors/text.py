"""Plain-text extractor.

Passthrough extractor that strips whitespace and validates
the document is not empty.

Usage::

    from src.ingestion.extractors.text import extract

    text = extract(raw_content)
"""

from __future__ import annotations


def extract(content: str) -> str:
    """Return *content* stripped of leading/trailing whitespace.

    Raises:
        ValueError: If content is empty or whitespace-only.
    """
    cleaned = content.strip()
    if not cleaned:
        raise ValueError("EMPTY_DOCUMENT")
    return cleaned
