"""Embedding generator via OpenRouter API.

Sends text batches to the OpenRouter embeddings endpoint and returns
vectors.  Uses ``httpx`` for async HTTP.

Usage::

    from src.ingestion.embedder import embed_texts

    vectors = await embed_texts(
        texts=["hello", "world"],
        base_url=settings.OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY,
        model=settings.EMBEDDING_MODEL,
    )
"""

from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)

_embed_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)


@_embed_retry
async def embed_texts(
    texts: list[str],
    *,
    base_url: str,
    api_key: str,
    model: str,
) -> list[list[float]]:
    """Generate embeddings for *texts* via the OpenRouter API.

    Args:
        texts: List of strings to embed.
        base_url: OpenRouter base URL (e.g. ``https://openrouter.ai/api/v1``).
        api_key: API key for authentication.
        model: Embedding model identifier.

    Returns:
        List of embedding vectors (each a list of floats).

    Raises:
        RuntimeError: On API error or unexpected response shape.
    """
    if not texts:
        return []

    url = f"{base_url.rstrip('/')}/embeddings"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            url,
            json={"input": texts, "model": model},
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code != 200:
        logger.error(
            "embedding_api_error",
            status=resp.status_code,
            body=resp.text[:500],
        )
        raise RuntimeError(
            f"Embedding API failed with status {resp.status_code}"
        )

    data = resp.json()
    try:
        # Sort by index to ensure correct order
        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"Unexpected embedding response shape: {exc}") from exc
