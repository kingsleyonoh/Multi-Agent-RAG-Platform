"""URL extractor.

Fetches a URL via ``httpx`` and extracts visible text using
BeautifulSoup.  Script and style tags are removed before extraction.

Usage::

    from src.ingestion.extractors.url import extract

    text = await extract("https://example.com/page")
"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup


async def extract(url: str) -> str:
    """Fetch *url* and return the visible text content.

    Raises:
        ValueError: On non-200 status or empty body after parsing.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, follow_redirects=True)

    if resp.status_code != 200:
        raise ValueError(
            f"Failed to fetch URL (status {resp.status_code}): {url}"
        )

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove non-visible elements
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True).strip()
    if not text:
        raise ValueError("EMPTY_DOCUMENT")
    return text
