"""Markdown extractor.

Strips YAML front-matter (delimited by ``---``) and returns the
remaining Markdown body.

Usage::

    from src.ingestion.extractors.markdown import extract

    body = extract(raw_markdown_string)
"""

from __future__ import annotations

import re


_FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n?", re.DOTALL)


def extract(content: str) -> str:
    """Strip YAML front-matter and return the Markdown body.

    Raises:
        ValueError: If the body is empty after stripping.
    """
    body = _FRONTMATTER_RE.sub("", content).strip()
    if not body:
        raise ValueError("EMPTY_DOCUMENT")
    return body
