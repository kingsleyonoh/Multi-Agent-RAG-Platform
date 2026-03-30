"""L1 — Deep Redis integration tests.

Tests the rate-limit INCR/EXPIRE pattern, TTL expiry, cache value
round-trips, and atomic concurrent operations against a live Redis
instance (Docker).
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid

import pytest

pytestmark = pytest.mark.integration

# Unique key prefix to avoid collisions.
_PREFIX = f"test:{uuid.uuid4().hex[:8]}"


# ── Helpers ──────────────────────────────────────────────────────


def _key(suffix: str) -> str:
    return f"{_PREFIX}:{suffix}"


# ── Rate Limit Counter Pattern ───────────────────────────────────


class TestRateLimitPattern:
    """Reproduce the exact INCR + EXPIRE pattern from rate_limit.py."""

    @pytest.fixture(autouse=True)
    async def _cleanup(self, redis_client):
        yield
        # Delete all keys with our prefix
        keys = []
        async for key in redis_client.scan_iter(f"{_PREFIX}:*"):
            keys.append(key)
        if keys:
            await redis_client.delete(*keys)

    async def test_incr_and_expire_pattern(self, redis_client):
        """Simulate the middleware: INCR, set EXPIRE on first hit."""
        key = _key("ratelimit:apikey:/api/chat:2024")
        count = await redis_client.incr(key)
        assert count == 1
        # First hit sets expiry
        await redis_client.expire(key, 60)

        count = await redis_client.incr(key)
        assert count == 2

        ttl = await redis_client.ttl(key)
        assert 50 <= ttl <= 60

    async def test_counter_exceeds_limit(self, redis_client):
        """INCR 31 times to exceed the 30/min chat sync limit."""
        key = _key("ratelimit:exceed")
        for _ in range(31):
            await redis_client.incr(key)

        count = int(await redis_client.get(key))
        assert count == 31
        assert count > 30  # exceeds /api/chat/sync limit

    async def test_key_format_matches_middleware(self, redis_client):
        """Verify the key format the middleware would construct."""
        api_key = "dev-key-1"
        path = "/api/documents"
        minute = "202603301200"
        key = f"ratelimit:{api_key}:{path}:{minute}"

        await redis_client.set(key, "5")
        val = await redis_client.get(key)
        assert val == "5"
        await redis_client.delete(key)


# ── TTL Expiry ───────────────────────────────────────────────────


class TestTTLExpiry:
    """Test that Redis key expiry works as expected."""

    async def test_key_expires_after_ttl(self, redis_client):
        key = _key("ttl_test")
        await redis_client.set(key, "value", ex=1)

        # Should exist immediately
        assert await redis_client.exists(key) == 1

        # Wait for expiry
        await asyncio.sleep(2)

        # Should be gone
        assert await redis_client.exists(key) == 0


# ── Cache Value Round-Trip ───────────────────────────────────────


class TestCacheRoundTrip:
    """Store and retrieve JSON cache entries."""

    @pytest.fixture(autouse=True)
    async def _cleanup(self, redis_client):
        yield
        keys = []
        async for key in redis_client.scan_iter(f"{_PREFIX}:*"):
            keys.append(key)
        if keys:
            await redis_client.delete(*keys)

    async def test_json_cache_round_trip(self, redis_client):
        key = _key("cache:query1")
        entry = {
            "query": "What is RAG?",
            "response": "RAG is Retrieval-Augmented Generation.",
            "model": "openai/gpt-4o-mini",
            "score": 0.95,
        }
        await redis_client.set(key, json.dumps(entry))

        raw = await redis_client.get(key)
        loaded = json.loads(raw)
        assert loaded["query"] == "What is RAG?"
        assert loaded["score"] == 0.95


# ── Concurrent Atomicity ────────────────────────────────────────


class TestConcurrentAtomicity:
    """Verify INCR atomicity under concurrent access."""

    async def test_concurrent_incr_is_atomic(self, redis_client):
        key = _key("atomic_incr")
        n = 10

        # Fire 10 concurrent INCRs
        results = await asyncio.gather(
            *(redis_client.incr(key) for _ in range(n))
        )

        # All 10 increments should succeed
        final = int(await redis_client.get(key))
        assert final == n

        # Results should be unique integers 1..10
        assert sorted(results) == list(range(1, n + 1))
        await redis_client.delete(key)
