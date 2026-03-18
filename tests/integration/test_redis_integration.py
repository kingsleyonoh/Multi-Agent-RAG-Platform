"""Smoke test: verify local Redis connectivity via TEST_REDIS_URL."""

import os

import pytest


@pytest.mark.integration
async def test_redis_connectivity():
    """PING local Redis and verify it responds.

    This validates:
    - Docker Redis is running on the expected port
    - TEST_REDIS_URL is correctly configured
    - redis-py async driver connects successfully
    """
    url = os.getenv("TEST_REDIS_URL")
    if not url:
        pytest.skip("TEST_REDIS_URL not set — skipping Redis integration test")

    from src.db.redis import get_client, ping, close_client

    client = get_client(url)
    try:
        result = await ping(client)
        assert result is True
    finally:
        await close_client(client)
