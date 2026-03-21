"""Smoke test: verify local PostgreSQL connectivity via TEST_DATABASE_URL."""

import pytest
from sqlalchemy import text


@pytest.mark.integration
async def test_postgres_connectivity(async_engine):
    """Connect to local PostgreSQL and verify it responds to a simple query.

    This validates:
    - Docker PostgreSQL is running on the expected port
    - TEST_DATABASE_URL is correctly configured
    - asyncpg driver connects successfully
    """
    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1 AS connected"))
        row = result.one()
        assert row.connected == 1
