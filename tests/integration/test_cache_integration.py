"""L2 — Semantic cache integration tests.

Tests the SemanticCache store/lookup/expiry/invalidation/stats
using pre-computed embeddings (no external API calls).
"""

from __future__ import annotations

import pytest

from src.cache.semantic import SemanticCache

pytestmark = pytest.mark.integration


# ── Helpers ──────────────────────────────────────────────────────


def _vec(val: float, dim: int = 10) -> list[float]:
    """Return a uniform vector (all elements = val)."""
    return [val] * dim


# ── Tests ────────────────────────────────────────────────────────


class TestSemanticCacheStoreAndLookup:
    """Store / lookup / miss / hit flow."""

    async def test_store_and_lookup_hit(self):
        cache = SemanticCache(similarity_threshold=0.95)
        emb = _vec(1.0)
        cache.store("What is RAG?", "RAG is Retrieval-Augmented Generation.", emb)

        # Lookup with the exact same embedding (similarity = 1.0)
        # We override _embed_query to return the same embedding
        cache._embed_query = lambda q: emb  # noqa: ARG005
        # _embed_query is async, need an async version
        async def _fake_embed(q):
            return emb
        cache._embed_query = _fake_embed

        hit = await cache.lookup("What is RAG?")
        assert hit is not None
        assert hit["response"] == "RAG is Retrieval-Augmented Generation."
        assert hit["similarity"] == pytest.approx(1.0)

    async def test_miss_for_different_query(self):
        cache = SemanticCache(similarity_threshold=0.95)
        cache.store("What is RAG?", "RAG response.", _vec(1.0))

        # Different embedding → low similarity → miss
        async def _fake_embed(q):
            return _vec(-1.0)
        cache._embed_query = _fake_embed

        hit = await cache.lookup("Something completely different")
        assert hit is None


class TestSemanticCacheTTL:
    """TTL expiry behavior."""

    async def test_expired_entries_return_none(self):
        cache = SemanticCache(similarity_threshold=0.95, ttl_hours=0)
        emb = _vec(1.0)
        cache.store("query", "response", emb)

        # TTL = 0 means entry is immediately expired
        async def _fake_embed(q):
            return emb
        cache._embed_query = _fake_embed

        # The entry is expired because ttl_hours=0 → 0 seconds TTL
        # created_at is now, now - created_at = ~0 which is > 0*3600
        hit = await cache.lookup("query")
        assert hit is None


class TestSemanticCacheStats:
    """Statistics tracking (lookups, hits, hit_rate)."""

    async def test_stats_tracking(self):
        cache = SemanticCache(similarity_threshold=0.95)
        emb = _vec(1.0)
        cache.store("cached query", "cached response", emb)

        async def _hit_embed(q):
            return emb
        async def _miss_embed(q):
            return _vec(-1.0)

        # 2 hits
        cache._embed_query = _hit_embed
        await cache.lookup("cached query")
        await cache.lookup("cached query")

        # 1 miss
        cache._embed_query = _miss_embed
        await cache.lookup("different")

        stats = cache.get_stats()
        assert stats["total_lookups"] == 3
        assert stats["total_hits"] == 2
        assert stats["hit_rate"] == pytest.approx(2 / 3, abs=0.01)
        assert stats["estimated_cost_saved"] > 0


class TestSemanticCacheInvalidation:
    """Invalidate all entries."""

    async def test_invalidate_all_clears_everything(self):
        cache = SemanticCache(similarity_threshold=0.95)
        cache.store("q1", "r1", _vec(1.0))
        cache.store("q2", "r2", _vec(0.5))
        assert len(cache.entries) == 2

        cache.invalidate_all()
        assert len(cache.entries) == 0

        stats = cache.get_stats()
        assert stats["total_entries"] == 0
        assert stats["total_lookups"] == 0
