"""Unit tests for src/db/redis – async Redis client wrapper (mocked).

All tests use ``unittest.mock`` so no running Redis instance is needed.
Follows the same structure as test_neo4j.py for consistency.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.redis import get_client, ping, close_client


# ── Fixtures ────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_client_cache():
    """Reset module-level client cache between tests."""
    from src.db import redis as mod
    mod._clients.clear()
    yield
    mod._clients.clear()


# ── get_client ──────────────────────────────────────────────────

class TestGetClient:
    """Verify cached async client creation."""

    @patch("src.db.redis.Redis")
    def test_returns_redis_client(self, mock_redis_cls: MagicMock) -> None:
        """get_client() returns a Redis instance."""
        mock_client = MagicMock()
        mock_redis_cls.from_url.return_value = mock_client

        result = get_client("redis://localhost:6379/0")

        mock_redis_cls.from_url.assert_called_once_with(
            "redis://localhost:6379/0", decode_responses=True
        )
        assert result is mock_client

    @patch("src.db.redis.Redis")
    def test_caches_by_url(self, mock_redis_cls: MagicMock) -> None:
        """Same URL returns the exact same client object (cached)."""
        mock_client = MagicMock()
        mock_redis_cls.from_url.return_value = mock_client

        c1 = get_client("redis://localhost:6379/0")
        c2 = get_client("redis://localhost:6379/0")

        assert c1 is c2
        assert mock_redis_cls.from_url.call_count == 1

    @patch("src.db.redis.Redis")
    def test_different_urls_different_clients(self, mock_redis_cls: MagicMock) -> None:
        """Different URLs produce distinct client instances."""
        mock_redis_cls.from_url.side_effect = [MagicMock(), MagicMock()]

        c1 = get_client("redis://localhost:6379/0")
        c2 = get_client("redis://localhost:6379/1")

        assert c1 is not c2
        assert mock_redis_cls.from_url.call_count == 2


# ── ping ────────────────────────────────────────────────────────

class TestPing:
    """Health check with graceful degradation."""

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self) -> None:
        """ping() returns True when server responds."""
        client = AsyncMock()
        client.ping.return_value = True

        result = await ping(client)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_error(self) -> None:
        """ping() returns False on connection error (graceful degradation)."""
        client = AsyncMock()
        client.ping.side_effect = Exception("Connection refused")

        result = await ping(client)

        assert result is False


# ── close_client ────────────────────────────────────────────────

class TestCloseClient:
    """Cleanup and cache eviction."""

    @pytest.mark.asyncio
    @patch("src.db.redis.Redis")
    async def test_closes_and_removes_from_cache(self, mock_redis_cls: MagicMock) -> None:
        """close_client() calls aclose() and removes client from module cache."""
        mock_client = AsyncMock()
        mock_redis_cls.from_url.return_value = mock_client

        client = get_client("redis://localhost:6379/0")

        # Verify client is in cache
        from src.db import redis as mod
        assert len(mod._clients) == 1

        await close_client(client)

        # Verify removed from cache and closed
        assert len(mod._clients) == 0
        mock_client.aclose.assert_awaited_once()
