"""Cache cleanup job.

Removes expired entries from the :class:`SemanticCache`.
Designed to run every 1 hour via a scheduler.

Usage::

    from src.cache.semantic import SemanticCache
    from src.jobs.cache_cleanup import cleanup_expired_entries

    removed = cleanup_expired_entries(cache)
"""

from __future__ import annotations

import time

from src.cache.semantic import SemanticCache


def cleanup_expired_entries(cache: SemanticCache) -> int:
    """Remove expired entries from *cache*.

    Returns the number of entries removed.
    """
    now = time.time()
    ttl_seconds = cache.ttl_hours * 3600

    before = len(cache.entries)
    cache.entries = [
        entry
        for entry in cache.entries
        if now - entry["created_at"] <= ttl_seconds
    ]
    return before - len(cache.entries)
