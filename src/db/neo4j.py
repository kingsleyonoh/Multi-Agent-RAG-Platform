"""Neo4j async driver wrapper — Shared Foundation module.

Provides cached driver creation, uniqueness-constraint initialisation,
connectivity verification with graceful degradation, and driver disposal.
Mirrors the pattern established by ``src/db/postgres.py``.

Public API
----------
get_driver(uri, user, password)  → neo4j.AsyncDriver (cached by URI)
init_constraints(driver)         → creates Entity uniqueness constraint
verify_connectivity(driver)      → True / False  (never raises)
close_driver(driver)             → disposes driver + removes from cache
"""

from __future__ import annotations

import logging
from typing import Dict

from neo4j import AsyncGraphDatabase, AsyncDriver

logger = logging.getLogger(__name__)

# ── Module-level cache ──────────────────────────────────────────
_drivers: Dict[str, AsyncDriver] = {}


# ── Public API ──────────────────────────────────────────────────

def get_driver(uri: str, user: str, password: str) -> AsyncDriver:
    """Return a cached :class:`AsyncDriver` for *uri*.

    If a driver for the same URI already exists it is returned as-is;
    otherwise a new one is created and stored in the module cache.
    """
    if uri in _drivers:
        return _drivers[uri]

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    _drivers[uri] = driver
    logger.info("Created Neo4j async driver for %s", uri)
    return driver


async def init_constraints(driver: AsyncDriver) -> None:
    """Create uniqueness constraint on ``Entity.id`` (idempotent).

    Uses ``CREATE CONSTRAINT IF NOT EXISTS`` so it is safe to call on
    every application startup.
    """
    query = (
        "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS "
        "FOR (e:Entity) REQUIRE e.id IS UNIQUE"
    )
    async with driver.session() as session:
        await session.run(query)
        logger.info("Neo4j Entity uniqueness constraint ensured")


async def verify_connectivity(driver: AsyncDriver) -> bool:
    """Check whether the Neo4j server is reachable.

    Returns ``True`` on success, ``False`` on any error — the
    application can therefore start even when Neo4j is unavailable
    (graceful degradation).
    """
    try:
        await driver.verify_connectivity()
        logger.info("Neo4j connectivity verified")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Neo4j unreachable: %s", exc)
        return False


async def close_driver(driver: AsyncDriver) -> None:
    """Close *driver* and remove it from the module cache."""
    # Remove from cache (match by identity)
    uri_to_remove = None
    for uri, cached in _drivers.items():
        if cached is driver:
            uri_to_remove = uri
            break
    if uri_to_remove is not None:
        del _drivers[uri_to_remove]

    await driver.close()
    logger.info("Neo4j driver closed")
