"""Semantic cache for RAG query responses.

Embeds the incoming query, searches the cache for a vector with cosine
similarity above the configured threshold.  On *hit* the cached response
is returned and ``hit_count`` is incremented.  On *miss* the caller
should process normally and then call :func:`store` to populate the
cache.

Entries are evicted when their TTL expires or when :func:`invalidate_all`
is called (e.g. after a new document is ingested).
"""

from __future__ import annotations

import math
import time
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ── helpers ──────────────────────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ── Estimated cost per LLM call (USD) for cost-saved calculation ──
_EST_COST_PER_CALL = 0.003


# ── SemanticCache ────────────────────────────────────────────────────


class SemanticCache:
    """In-memory semantic cache with cosine-similarity lookup.

    Parameters
    ----------
    similarity_threshold:
        Minimum cosine similarity to consider a cache hit (default 0.95).
    ttl_hours:
        Time-to-live for cache entries in hours (default 24).
    settings:
        App settings for real embedding via ``embed_texts()``.
        When ``None``, embeddings return ``[0.0]`` (test mode).
    """

    def __init__(
        self,
        *,
        similarity_threshold: float = 0.95,
        ttl_hours: int = 24,
        settings=None,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.ttl_hours = ttl_hours
        self._settings = settings
        self.entries: list[dict[str, Any]] = []
        self._total_lookups = 0
        self._total_hits = 0

    # ── public API ───────────────────────────────────────────────────

    async def lookup(self, query: str) -> dict[str, Any] | None:
        """Return cached response if a similar query exists, else *None*."""
        self._total_lookups += 1
        query_emb = await self._embed_query(query)
        now = time.time()

        for entry in self.entries:
            # skip expired
            if now - entry["created_at"] > self.ttl_hours * 3600:
                continue
            sim = _cosine_similarity(query_emb, entry["embedding"])
            if sim >= self.similarity_threshold:
                entry["hit_count"] += 1
                self._total_hits += 1
                return {
                    "response": entry["response"],
                    "similarity": sim,
                    "hit_count": entry["hit_count"],
                }
        return None

    def store(
        self,
        query: str,
        response: str,
        embedding: list[float],
    ) -> None:
        """Store a query / response pair with its pre-computed embedding."""
        self.entries.append(
            {
                "query": query,
                "response": response,
                "embedding": embedding,
                "created_at": time.time(),
                "hit_count": 0,
            }
        )

    def invalidate_all(self) -> None:
        """Clear every entry and reset counters."""
        self.entries.clear()
        self._total_lookups = 0
        self._total_hits = 0

    def get_stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        hit_rate = (
            self._total_hits / self._total_lookups
            if self._total_lookups > 0
            else 0.0
        )
        return {
            "total_entries": len(self.entries),
            "total_lookups": self._total_lookups,
            "total_hits": self._total_hits,
            "hit_rate": round(hit_rate, 4),
            "estimated_cost_saved": round(
                self._total_hits * _EST_COST_PER_CALL, 4
            ),
        }

    # ── seams (override in tests / production) ───────────────────────

    async def _embed_query(self, query: str) -> list[float]:
        """Embed a query string for similarity comparison.

        Uses real ``embed_texts()`` when settings are available.
        Returns ``[0.0]`` in test/fallback mode.
        """
        if self._settings is None:
            return [0.0]

        from src.ingestion.embedder import embed_texts

        try:
            embeddings = await embed_texts(
                texts=[query],
                base_url=self._settings.OPENROUTER_BASE_URL,
                api_key=self._settings.OPENROUTER_API_KEY,
                model=self._settings.EMBEDDING_MODEL,
            )
            return embeddings[0]
        except Exception:
            logger.warning("cache_embed_failed", exc_info=True)
            return [0.0]
