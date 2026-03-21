"""Async Redis client wrapper — Shared Foundation module.

Provides cached client creation, health-check with graceful degradation,
and client disposal.  Mirrors the pattern established by ``src/db/neo4j.py``.

Public API
----------
get_client(url)      → redis.asyncio.Redis  (cached by URL)
ping(client)         → True / False          (never raises)
close_client(client) → disposes client + removes from cache
"""

from __future__ import annotations

import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# ── Module-level cache ──────────────────────────────────────────
_clients: dict[str, Redis] = {}


# ── Public API ──────────────────────────────────────────────────

def get_client(url: str) -> Redis:
    """Return a cached async :class:`Redis` client for *url*.

    If a client for the same URL already exists it is returned as-is;
    otherwise a new one is created via ``Redis.from_url`` and stored
    in the module cache.
    """
    if url in _clients:
        return _clients[url]

    client = Redis.from_url(url, decode_responses=True)
    _clients[url] = client
    logger.info("Created Redis async client for %s", url)
    return client


async def ping(client: Redis) -> bool:
    """Check whether the Redis server is reachable.

    Returns ``True`` on success, ``False`` on any error — the
    application can therefore start even when Redis is unavailable
    (graceful degradation).
    """
    try:
        await client.ping()
        logger.info("Redis connectivity verified")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis unreachable: %s", exc)
        return False


async def close_client(client: Redis) -> None:
    """Close *client* and remove it from the module cache."""
    # Remove from cache (match by identity)
    url_to_remove = None
    for url, cached in _clients.items():
        if cached is client:
            url_to_remove = url
            break
    if url_to_remove is not None:
        del _clients[url_to_remove]

    await client.aclose()
    logger.info("Redis client closed")
