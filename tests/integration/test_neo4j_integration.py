"""Integration tests for src/db/neo4j – requires a running Neo4j instance."""

from __future__ import annotations

import os

import pytest

from src.db.neo4j import close_driver, get_driver, init_constraints, verify_connectivity


# ── Helpers ─────────────────────────────────────────────────────

def _neo4j_creds() -> tuple[str, str, str]:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "devpass1")
    return uri, user, password


# ── Fixtures ────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_cache():
    from src.db import neo4j as mod
    mod._drivers.clear()
    yield
    mod._drivers.clear()


@pytest.fixture
async def driver():
    """Provide a fresh driver; close it after the test."""
    uri, user, password = _neo4j_creds()
    drv = get_driver(uri, user, password)
    yield drv
    await close_driver(drv)


# ── Tests ───────────────────────────────────────────────────────

class TestNeo4jIntegration:

    @pytest.mark.asyncio
    async def test_verify_connectivity_returns_true(self, driver) -> None:
        ok = await verify_connectivity(driver)
        assert ok is True

    @pytest.mark.asyncio
    async def test_init_constraints_creates_entity_constraint(self, driver) -> None:
        await init_constraints(driver)

        # Query Neo4j for existing constraints
        async with driver.session() as session:
            result = await session.run("SHOW CONSTRAINTS")
            records = [r async for r in result]

        names = [r["name"] for r in records]
        assert any("entity" in n.lower() for n in names), (
            f"Expected an Entity uniqueness constraint, got: {names}"
        )

    @pytest.mark.asyncio
    async def test_close_driver_removes_from_cache(self, driver) -> None:
        from src.db import neo4j as mod

        uri, _, _ = _neo4j_creds()
        assert uri in mod._drivers

        await close_driver(driver)

        assert uri not in mod._drivers
