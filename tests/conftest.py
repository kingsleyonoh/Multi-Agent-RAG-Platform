"""Shared test fixtures for the Multi-Agent RAG Platform.

Loads environment from .env and provides async database session fixtures.
"""

import os
from collections.abc import AsyncGenerator

import pytest
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Load .env before any test runs so TEST_DATABASE_URL is available.
load_dotenv()


@pytest.fixture(scope="session")
def database_url() -> str:
    """Return the test database URL from environment."""
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set — skipping DB tests")
    return url


@pytest.fixture(scope="session")
def async_engine(database_url: str):
    """Create a shared async engine for the test session."""
    engine = create_async_engine(database_url, echo=False)
    yield engine
    # Engine disposal is handled after all tests complete.


@pytest.fixture
async def async_session(
    async_engine,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async session that rolls back after each test."""
    session_factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        async with session.begin():
            yield session
            # Rollback ensures each test starts with a clean state.
            await session.rollback()
