"""Semantic cache for RAG query responses — pgvector-backed.

Embeds the incoming query, searches the ``semantic_cache`` table
for a vector with cosine similarity above the configured threshold.
On *hit* the cached response is returned and ``hit_count`` is
incremented.  On *miss* the caller should process normally and
then call :func:`store` to populate the cache.

Entries are evicted when their TTL expires or when
:func:`invalidate_all` is called (e.g. after a new document
is ingested).

Falls back to in-memory storage when no session factory is
available (e.g. tests without a database).
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker

logger = structlog.get_logger(__name__)

# Estimated cost per LLM call (USD) for cost-saved calculation.
_EST_COST_PER_CALL = 0.003


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


class SemanticCache:
    """pgvector-backed semantic cache with cosine-similarity lookup.

    When a session factory is provided, entries persist to the
    ``semantic_cache`` table.  Without one, falls back to in-memory
    storage.

    Parameters
    ----------
    similarity_threshold:
        Minimum cosine similarity to consider a cache hit (default 0.95).
    ttl_hours:
        Time-to-live for cache entries in hours (default 24).
    settings:
        App settings for real embedding via ``embed_texts()``.
    session_factory:
        SQLAlchemy async session factory for DB persistence.
    """

    def __init__(
        self,
        *,
        similarity_threshold: float = 0.95,
        ttl_hours: int = 24,
        settings=None,
        session_factory: async_sessionmaker | None = None,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.ttl_hours = ttl_hours
        self._settings = settings
        self._session_factory = session_factory
        # In-memory fallback
        self.entries: list[dict[str, Any]] = []
        self._total_lookups = 0
        self._total_hits = 0

    # ── public API ───────────────────────────────────────────────────

    async def lookup(self, query: str) -> dict[str, Any] | None:
        """Return cached response if a similar query exists, else *None*."""
        self._total_lookups += 1
        query_emb = await self._embed_query(query)

        if self._session_factory is not None:
            return await self._db_lookup(query_emb)

        return self._memory_lookup(query_emb)

    async def store(
        self,
        query: str,
        response: str,
        embedding: list[float],
    ) -> None:
        """Store a query / response pair with its pre-computed embedding."""
        if self._session_factory is not None:
            await self._db_store(query, response, embedding)
        else:
            self.entries.append({
                "query": query,
                "response": response,
                "embedding": embedding,
                "created_at": time.time(),
                "hit_count": 0,
            })

    def invalidate_all(self) -> None:
        """Clear every entry and reset counters (sync for compatibility)."""
        self.entries.clear()
        self._total_lookups = 0
        self._total_hits = 0
        # DB invalidation is async — call invalidate_all_async for DB
        if self._session_factory is not None:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._db_invalidate())
            except RuntimeError:
                pass  # No event loop — skip DB cleanup

    async def invalidate_all_async(self) -> None:
        """Async version of invalidate_all for DB-backed cache."""
        self.entries.clear()
        self._total_lookups = 0
        self._total_hits = 0
        if self._session_factory is not None:
            await self._db_invalidate()

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

    async def get_stats_async(self) -> dict[str, Any]:
        """Return cache statistics with DB entry count."""
        entry_count = len(self.entries)
        if self._session_factory is not None:
            try:
                async with self._session_factory() as session:
                    result = await session.execute(text(
                        "SELECT COUNT(*) FROM semantic_cache "
                        "WHERE expires_at > NOW()"
                    ))
                    entry_count = result.scalar() or 0
            except Exception:
                logger.warning("cache_stats_db_failed", exc_info=True)

        hit_rate = (
            self._total_hits / self._total_lookups
            if self._total_lookups > 0
            else 0.0
        )
        return {
            "total_entries": entry_count,
            "total_lookups": self._total_lookups,
            "total_hits": self._total_hits,
            "hit_rate": round(hit_rate, 4),
            "estimated_cost_saved": round(
                self._total_hits * _EST_COST_PER_CALL, 4
            ),
        }

    # ── DB operations ────────────────────────────────────────────────

    async def _db_lookup(self, query_emb: list[float]) -> dict[str, Any] | None:
        """Search semantic_cache table via pgvector cosine similarity."""
        try:
            vec_str = "[" + ",".join(str(v) for v in query_emb) + "]"
            async with self._session_factory() as session:
                result = await session.execute(
                    text(
                        "SELECT id, query_text, response, hit_count, "
                        "1 - (query_embedding <=> cast(:vec AS vector)) AS similarity "
                        "FROM semantic_cache "
                        "WHERE expires_at > NOW() "
                        "AND 1 - (query_embedding <=> cast(:vec AS vector)) >= :threshold "
                        "ORDER BY similarity DESC LIMIT 1"
                    ),
                    {"vec": vec_str, "threshold": self.similarity_threshold},
                )
                row = result.first()
                if row is None:
                    return None

                # Increment hit count
                await session.execute(
                    text(
                        "UPDATE semantic_cache SET hit_count = hit_count + 1 "
                        "WHERE id = :id"
                    ),
                    {"id": row.id},
                )
                await session.commit()

                self._total_hits += 1
                return {
                    "response": row.response,
                    "similarity": float(row.similarity),
                    "hit_count": row.hit_count + 1,
                }
        except Exception:
            logger.warning("cache_db_lookup_failed", exc_info=True)
            return None

    async def _db_store(
        self, query: str, response: str, embedding: list[float],
    ) -> None:
        """Insert a cache entry into the semantic_cache table."""
        try:
            from src.db.models import SemanticCache as CacheModel

            expires = datetime.now(timezone.utc) + timedelta(hours=self.ttl_hours)
            async with self._session_factory() as session:
                session.add(CacheModel(
                    query_embedding=embedding,
                    query_text=query,
                    response=response,
                    model_used="cache",
                    expires_at=expires,
                ))
                await session.commit()
        except Exception:
            logger.warning("cache_db_store_failed", exc_info=True)

    async def _db_invalidate(self) -> None:
        """Delete all cache entries from the DB."""
        try:
            async with self._session_factory() as session:
                await session.execute(text("DELETE FROM semantic_cache"))
                await session.commit()
        except Exception:
            logger.warning("cache_db_invalidate_failed", exc_info=True)

    # ── In-memory fallback ───────────────────────────────────────────

    def _memory_lookup(self, query_emb: list[float]) -> dict[str, Any] | None:
        """Search in-memory entries by cosine similarity."""
        now = time.time()
        for entry in self.entries:
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

    # ── seams ────────────────────────────────────────────────────────

    async def _embed_query(self, query: str) -> list[float]:
        """Embed a query string for similarity comparison."""
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
