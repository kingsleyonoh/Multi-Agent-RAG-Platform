"""Shared test fixtures for the Multi-Agent RAG Platform.

Loads environment from .env and provides async database session fixtures,
LLM mock infrastructure via respx, and live integration test fixtures
for Neo4j, Redis, and the running server.
"""

import json
import os
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest
import respx
from dotenv import load_dotenv
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Load .env before any test runs so TEST_DATABASE_URL is available.
load_dotenv()

# Path to fixture files.
FIXTURES_DIR = Path(__file__).parent / "fixtures"
LLM_FIXTURES_DIR = FIXTURES_DIR / "llm" / "openrouter_responses"

# Live server URL for API integration and E2E tests.
LIVE_SERVER_URL = os.getenv("TEST_SERVER_URL", "http://127.0.0.1:8000")


def load_fixture(name: str) -> dict:
    """Load a JSON fixture file from tests/fixtures/llm/openrouter_responses/.

    Args:
        name: Filename without extension, e.g. 'chat_completion'.

    Returns:
        Parsed JSON as a dict.
    """
    filepath = LLM_FIXTURES_DIR / f"{name}.json"
    return json.loads(filepath.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Database Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def database_url() -> str:
    """Return the test database URL from environment."""
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set — skipping DB tests")
    return url


@pytest.fixture(scope="session")
def async_engine(database_url: str):
    """Create a shared async engine for the test session.

    Uses NullPool so each connection is fresh — avoids asyncpg
    event-loop binding issues across function-scoped tests.
    """
    engine = create_async_engine(database_url, echo=False, poolclass=NullPool)
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


@pytest.fixture
async def committed_session(
    async_engine,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a session that commits (for tests verifying persisted data).

    The caller is responsible for cleanup (DELETE rows created).
    """
    session_factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Neo4j Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def neo4j_uri() -> str:
    """Return the Neo4j URI from environment."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    return uri


@pytest.fixture(scope="session")
def neo4j_credentials() -> tuple[str, str]:
    """Return (user, password) for Neo4j."""
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "testpassword")
    return user, password


@pytest.fixture
async def neo4j_driver(neo4j_uri, neo4j_credentials):
    """Provide a real Neo4j async driver per test (fresh connection)."""
    from neo4j import AsyncGraphDatabase

    user, password = neo4j_credentials
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(user, password))
    try:
        await driver.verify_connectivity()
    except Exception:
        await driver.close()
        pytest.skip("Neo4j not available — skipping Neo4j tests")
        return
    yield driver
    await driver.close()


# ---------------------------------------------------------------------------
# Redis Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def redis_url() -> str:
    """Return the Redis URL from environment."""
    return os.getenv("TEST_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6380"))


@pytest.fixture
async def redis_client(redis_url):
    """Provide a real async Redis client per test (fresh connection)."""
    from redis.asyncio import Redis

    client = Redis.from_url(redis_url, decode_responses=True)
    try:
        await client.ping()
    except Exception:
        await client.aclose()
        pytest.skip("Redis not available — skipping Redis tests")
        return
    yield client
    await client.aclose()


# ---------------------------------------------------------------------------
# Settings Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def live_settings():
    """Return the real Settings instance (reads from .env)."""
    from src.config import get_settings
    return get_settings()


# ---------------------------------------------------------------------------
# HTTP Client Fixtures (for API integration / E2E tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def auth_headers() -> dict[str, str]:
    """Return auth headers for the live server."""
    return {
        "X-API-Key": os.getenv("TEST_API_KEY", "dev-key-1"),
        "X-User-Id": "e2e-test-user",
    }


@pytest.fixture
async def httpx_client(auth_headers) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async HTTP client pointed at the live server."""
    async with httpx.AsyncClient(
        base_url=LIVE_SERVER_URL,
        headers=auth_headers,
        timeout=60.0,
    ) as client:
        yield client


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

