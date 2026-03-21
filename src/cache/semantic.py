"""Semantic cache for RAG query responses.

Embeds the incoming query, searches the cache for a vector with cosine
similarity above the configured threshold.  On *hit* the cached response
is returned and ``hit_count`` is incremented.  On *miss* the caller
should process normally and then call :func:`store` to populate the
cache.

Entries are evicted when their TTL expires or when :func:`invalidate_all`
is called (e.g. after a new document is ingested).

An LRU helper (:func:`lru_embed`) avoids re-embedding identical query
strings within the same session.
"""

from __future__ import annotations

import math
import time
from functools import lru_cache
from typing import Any


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


# ── LRU embedding cache ─────────────────────────────────────────────

@lru_cache(maxsize=256)
def lru_embed(query: str, *, embed_fn: Any = None) -> list[float]:
    """Return the embedding for *query*, caching repeat calls.

    Parameters
    ----------
    query:
        The text to embed.
    embed_fn:
        A callable ``(str) -> list[float]``.  When *None* the internal
        ``_embed_query`` seam is used.
    """
    if embed_fn is None:
        return _embed_query_default(query)
    return embed_fn(query)


def _embed_query_default(query: str) -> list[float]:
    """Seam — override in production to call the real embedding API."""
    return [0.0]


# ── SemanticCache ────────────────────────────────────────────────────

# Estimated cost per LLM call (USD) for cost-saved calculation.
_EST_COST_PER_CALL = 0.003


class SemanticCache:
    """In-memory semantic cache with cosine-similarity lookup.

    Parameters
    ----------
    similarity_threshold:
        Minimum cosine similarity to consider a cache hit (default 0.95).
    ttl_hours:
        Time-to-live for cache entries in hours (default 24).
    """

    def __init__(
        self,
        *,
        similarity_threshold: float = 0.95,
        ttl_hours: int = 24,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.ttl_hours = ttl_hours
        self.entries: list[dict[str, Any]] = []
        self._total_lookups = 0
        self._total_hits = 0

    # ── public API ───────────────────────────────────────────────────

    def lookup(self, query: str) -> dict[str, Any] | None:
        """Return cached response if a similar query exists, else *None*."""
        self._total_lookups += 1
        query_emb = self._embed_query(query)
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

    def _embed_query(self, query: str) -> list[float]:
        """Seam — override to call real embedding API."""
        return _embed_query_default(query)
