"""Application configuration using Pydantic settings.

Validates all PRD §14 environment variables on startup. Required fields
raise ``ValidationError`` when missing; optional fields apply defaults
from the PRD specification.

Usage::

    from src.config import get_settings
    settings = get_settings()
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Validated application settings loaded from environment / .env file.

    Required fields have no default and will raise ``ValidationError``
    if the corresponding env var is absent.
    """

    # ------------------------------------------------------------------
    # Server
    # ------------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = Field(default=8008, ge=1, le=65535)
    ENV: Literal["development", "production", "testing"] = "development"
    API_KEYS: str = "dev-key-1"
    LOG_LEVEL: Literal["debug", "info", "warning", "error"] = "info"

    # ------------------------------------------------------------------
    # Databases (required — no usable defaults)
    # ------------------------------------------------------------------
    DATABASE_URL: str
    NEO4J_URI: str
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "devpass1"
    REDIS_URL: str

    # ------------------------------------------------------------------
    # LLM Provider (required — no usable default for API key)
    # ------------------------------------------------------------------
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_APP_NAME: str = "multi-agent-rag-platform"

    # ------------------------------------------------------------------
    # LLM Model Selection
    # ------------------------------------------------------------------
    DEFAULT_MODEL: str = "openai/gpt-4o-mini"
    EMBEDDING_MODEL: str = "openai/text-embedding-3-small"
    MEMORY_SUMMARY_MODEL: str = "google/gemini-2.0-flash-exp"
    EVAL_JUDGE_MODEL: str = "openai/gpt-4o-mini"

    # ------------------------------------------------------------------
    # RAG Configuration
    # ------------------------------------------------------------------
    CHUNK_SIZE: int = Field(default=512, ge=1)
    CHUNK_OVERLAP: int = Field(default=50, ge=0)
    RETRIEVAL_TOP_K: int = Field(default=10, ge=1)
    RERANK_TOP_N: int = Field(default=5, ge=1)
    SIMILARITY_THRESHOLD: float = Field(default=0.7, ge=0.0, le=1.0)

    # ------------------------------------------------------------------
    # Guardrails
    # ------------------------------------------------------------------
    GUARDRAIL_INJECTION_THRESHOLD: float = Field(default=0.8, ge=0.0, le=1.0)
    GUARDRAIL_PII_MODE: Literal["flag", "redact", "block"] = "flag"

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------
    CACHE_SIMILARITY_THRESHOLD: float = Field(default=0.95, ge=0.0, le=1.0)
    CACHE_TTL_HOURS: int = Field(default=24, ge=1)

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------
    MAX_TOOL_CALLS_PER_TURN: int = Field(default=5, ge=1)
    MOCK_LLM: bool = False

    # ------------------------------------------------------------------
    # Cost Management
    # ------------------------------------------------------------------
    DAILY_COST_LIMIT_USD: float = Field(default=10.0, ge=0.0)

    # ------------------------------------------------------------------
    # MCP
    # ------------------------------------------------------------------
    MCP_SERVER_PORT: int = Field(default=3001, ge=1, le=65535)
    MCP_TRANSPORT: Literal["stdio", "sse"] = "stdio"

    # ------------------------------------------------------------------
    # Feature Flags
    # ------------------------------------------------------------------
    DEMO_MODE: bool = False

    # ------------------------------------------------------------------
    # Test
    # ------------------------------------------------------------------
    TEST_DATABASE_URL: str | None = None

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of the validated settings."""
    return Settings()
