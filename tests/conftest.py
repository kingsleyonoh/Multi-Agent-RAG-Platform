"""Shared test fixtures for the Multi-Agent RAG Platform.

Loads environment from .env and provides async database session fixtures
and LLM mock infrastructure via respx.
"""

import json
import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import respx
from dotenv import load_dotenv
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Load .env before any test runs so TEST_DATABASE_URL is available.
load_dotenv()

# Path to fixture files.
FIXTURES_DIR = Path(__file__).parent / "fixtures"
LLM_FIXTURES_DIR = FIXTURES_DIR / "llm" / "openrouter_responses"


def load_fixture(name: str) -> dict:
    """Load a JSON fixture file from tests/fixtures/llm/openrouter_responses/.

    Args:
        name: Filename without extension, e.g. 'chat_completion'.

    Returns:
        Parsed JSON as a dict.
    """
    filepath = LLM_FIXTURES_DIR / f"{name}.json"
    return json.loads(filepath.read_text(encoding="utf-8"))


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


# ---------------------------------------------------------------------------
# LLM Mock Infrastructure
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mock_llm() -> bool:
    """Return True when MOCK_LLM=true in environment.

    Use this to conditionally skip or alter test behavior:
    - MOCK_LLM=true  → tests use respx fixtures (fast, free, deterministic)
    - MOCK_LLM=false → tests hit real OpenRouter API (integration testing)
    """
    return os.getenv("MOCK_LLM", "true").lower() == "true"


@pytest.fixture
def mock_openrouter():
    """Intercept all HTTP requests to OpenRouter and return fixture responses.

    Usage in tests:
        def test_llm_call(mock_openrouter):
            mock_openrouter.post(
                "https://openrouter.ai/api/v1/chat/completions"
            ).mock(return_value=Response(200, json=load_fixture("chat_completion")))
            # ... make your httpx call ...

    Returns the respx mock router for further configuration.
    """
    with respx.mock(assert_all_called=False) as router:
        yield router

