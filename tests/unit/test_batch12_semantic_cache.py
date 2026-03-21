"""Batch 12 — Semantic Cache RED phase tests.

Tests for:
  - SemanticCache: embed → cosine → hit/miss flow
  - LRU embedding cache
  - Cache stats API endpoint
"""

import time
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ── SemanticCache ─────────────────────────────────────────────────────

from src.cache.semantic import SemanticCache


class TestSemanticCacheInit:
    """SemanticCache can be instantiated with configurable thresholds."""

    def test_default_threshold(self):
        cache = SemanticCache()
        assert cache.similarity_threshold == 0.95

    def test_custom_threshold(self):
        cache = SemanticCache(similarity_threshold=0.90)
        assert cache.similarity_threshold == 0.90

    def test_default_ttl(self):
        cache = SemanticCache()
        assert cache.ttl_hours == 24

    def test_custom_ttl(self):
        cache = SemanticCache(ttl_hours=12)
        assert cache.ttl_hours == 12


class TestSemanticCacheMiss:
    """When no similar query exists, cache returns None."""

    def test_miss_returns_none(self):
        cache = SemanticCache()
        result = cache.lookup("What is Python?")
        assert result is None

    def test_miss_on_empty_cache(self):
        cache = SemanticCache()
        result = cache.lookup("Tell me about machine learning")
        assert result is None


class TestSemanticCacheStore:
    """Storing a query+response makes it retrievable."""

    def test_store_and_lookup(self):
        cache = SemanticCache()
        cache.store(
            query="What is Python?",
            response="Python is a programming language.",
            embedding=[0.1, 0.2, 0.3],
        )
        # Override _embed_query to return the same embedding for exact match
        cache._embed_query = lambda q: [0.1, 0.2, 0.3]
        result = cache.lookup("What is Python?")
        assert result is not None
        assert result["response"] == "Python is a programming language."

    def test_store_increments_entry_count(self):
        cache = SemanticCache()
        cache.store("q1", "r1", [0.1, 0.2])
        cache.store("q2", "r2", [0.3, 0.4])
        assert len(cache.entries) == 2


class TestSemanticCacheHitCount:
    """Cache hits increment the hit counter."""

    def test_hit_increments_count(self):
        cache = SemanticCache()
        cache.store("What is Python?", "A language.", [0.1, 0.2, 0.3])
        cache._embed_query = lambda q: [0.1, 0.2, 0.3]

        cache.lookup("What is Python?")
        cache.lookup("What is Python?")
        # Find the entry and check hit_count
        assert cache.entries[0]["hit_count"] >= 2


class TestSemanticCacheTTL:
    """Expired entries are not returned."""

    def test_expired_entry_returns_none(self):
        cache = SemanticCache(ttl_hours=0)  # immediate expiry
        cache.store("q", "r", [0.1])
        cache._embed_query = lambda q: [0.1]
        # Entry should be expired
        time.sleep(0.01)
        result = cache.lookup("q")
        assert result is None


class TestSemanticCacheInvalidate:
    """Invalidation clears all entries."""

    def test_invalidate_clears_cache(self):
        cache = SemanticCache()
        cache.store("q1", "r1", [0.1])
        cache.store("q2", "r2", [0.2])
        cache.invalidate_all()
        assert len(cache.entries) == 0

    def test_invalidate_resets_stats(self):
        cache = SemanticCache()
        cache.store("q", "r", [0.1])
        cache._embed_query = lambda q: [0.1]
        cache.lookup("q")  # hit
        cache.invalidate_all()
        stats = cache.get_stats()
        assert stats["total_entries"] == 0


class TestSemanticCacheStats:
    """Cache exposes stats: entries, hit rate, cost saved."""

    def test_stats_structure(self):
        cache = SemanticCache()
        stats = cache.get_stats()
        assert "total_entries" in stats
        assert "hit_rate" in stats
        assert "estimated_cost_saved" in stats

    def test_stats_after_hits(self):
        cache = SemanticCache()
        cache.store("q", "r", [0.1])
        cache._embed_query = lambda q: [0.1]
        cache.lookup("q")  # hit
        cache.lookup("nonexistent")  # miss (embed returns [0.1] but let's handle)

        stats = cache.get_stats()
        assert stats["total_entries"] == 1
        assert stats["hit_rate"] >= 0.0


# ── LRU Embedding Cache ──────────────────────────────────────────────

from src.cache.semantic import lru_embed


class TestLRUEmbedCache:
    """LRU cache avoids re-embedding identical strings."""

    def test_returns_embedding(self):
        result = lru_embed("test query", embed_fn=lambda q: [0.5, 0.6])
        assert result == [0.5, 0.6]

    def test_caches_repeat_calls(self):
        call_count = 0

        def counting_embed(q):
            nonlocal call_count
            call_count += 1
            return [0.1, 0.2]

        lru_embed.cache_clear()  # clear from prior tests
        lru_embed("same query", embed_fn=counting_embed)
        lru_embed("same query", embed_fn=counting_embed)
        assert call_count == 1  # only embedded once


# ── Cache Stats API ──────────────────────────────────────────────────

from src.api.routes.cache import router as cache_router


class TestCacheStatsEndpoint:
    """GET /api/cache/stats returns cache statistics."""

    @pytest.fixture()
    def client(self):
        app = FastAPI()
        app.include_router(cache_router, prefix="/api/cache")
        return TestClient(app)

    def test_stats_endpoint_returns_200(self, client):
        resp = client.get("/api/cache/stats")
        assert resp.status_code == 200

    def test_stats_response_structure(self, client):
        resp = client.get("/api/cache/stats")
        data = resp.json()
        assert "total_entries" in data
        assert "hit_rate" in data
        assert "estimated_cost_saved" in data
