"""Config validation tests — RED phase.

Tests that the Pydantic settings model correctly validates all PRD §14
environment variables: required fields, types, defaults, ranges, and enums.
"""

import pytest
from pydantic import ValidationError

from src.config import Settings


# ---------------------------------------------------------------------------
# Minimal valid config — all required fields present
# ---------------------------------------------------------------------------

VALID_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://postgres:devpass1@localhost:5433/ragplatform",
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "devpass1",
    "REDIS_URL": "redis://localhost:6380",
    "OPENROUTER_API_KEY": "sk-or-v1-test-key",
}


class _NoEnvSettings(Settings):
    """Settings subclass that ignores .env file and environment variables.

    Used in required-field tests to verify that missing kwargs actually
    raise ``ValidationError`` rather than being silently filled from .env.
    """

    model_config = {
        "env_file": None,
        "env_ignore_empty": True,
        "case_sensitive": True,
        "env_prefix": "___TEST_ISOLATION___",
    }


class TestRequiredFields:
    """Settings must reject missing required fields."""

    def test_missing_database_url_raises(self):
        env = {**VALID_ENV}
        del env["DATABASE_URL"]
        with pytest.raises(ValidationError, match="DATABASE_URL"):
            _NoEnvSettings(**env)

    def test_missing_neo4j_uri_raises(self):
        env = {**VALID_ENV}
        del env["NEO4J_URI"]
        with pytest.raises(ValidationError, match="NEO4J_URI"):
            _NoEnvSettings(**env)

    def test_missing_redis_url_raises(self):
        env = {**VALID_ENV}
        del env["REDIS_URL"]
        with pytest.raises(ValidationError, match="REDIS_URL"):
            _NoEnvSettings(**env)

    def test_missing_openrouter_api_key_raises(self):
        env = {**VALID_ENV}
        del env["OPENROUTER_API_KEY"]
        with pytest.raises(ValidationError, match="OPENROUTER_API_KEY"):
            _NoEnvSettings(**env)


class TestDefaults:
    """Optional fields must apply correct defaults from PRD §14."""

    def test_port_defaults_to_8008(self):
        s = Settings(**VALID_ENV)
        assert s.PORT == 8008

    def test_env_defaults_to_development(self):
        s = Settings(**VALID_ENV)
        assert s.ENV == "development"

    def test_log_level_defaults_to_info(self):
        s = Settings(**VALID_ENV)
        assert s.LOG_LEVEL == "info"

    def test_chunk_size_defaults_to_512(self):
        s = Settings(**VALID_ENV)
        assert s.CHUNK_SIZE == 512

    def test_chunk_overlap_defaults_to_50(self):
        s = Settings(**VALID_ENV)
        assert s.CHUNK_OVERLAP == 50

    def test_retrieval_top_k_defaults_to_10(self):
        s = Settings(**VALID_ENV)
        assert s.RETRIEVAL_TOP_K == 10

    def test_rerank_top_n_defaults_to_5(self):
        s = Settings(**VALID_ENV)
        assert s.RERANK_TOP_N == 5

    def test_similarity_threshold_defaults_to_0_7(self):
        s = Settings(**VALID_ENV)
        assert s.SIMILARITY_THRESHOLD == 0.7

    def test_cache_ttl_hours_defaults_to_24(self):
        s = Settings(**VALID_ENV)
        assert s.CACHE_TTL_HOURS == 24

    def test_mock_llm_defaults_to_false(self):
        s = Settings(**VALID_ENV)
        assert s.MOCK_LLM is False

    def test_daily_cost_limit_defaults_to_10(self):
        s = Settings(**VALID_ENV)
        assert s.DAILY_COST_LIMIT_USD == 10.0


class TestTypeValidation:
    """Settings must reject invalid types."""

    def test_port_rejects_non_integer(self):
        with pytest.raises(ValidationError, match="PORT"):
            Settings(**{**VALID_ENV, "PORT": "abc"})

    def test_chunk_size_rejects_negative(self):
        with pytest.raises(ValidationError, match="CHUNK_SIZE"):
            Settings(**{**VALID_ENV, "CHUNK_SIZE": -1})

    def test_retrieval_top_k_rejects_zero(self):
        with pytest.raises(ValidationError, match="RETRIEVAL_TOP_K"):
            Settings(**{**VALID_ENV, "RETRIEVAL_TOP_K": 0})

    def test_daily_cost_limit_rejects_negative(self):
        with pytest.raises(ValidationError, match="DAILY_COST_LIMIT_USD"):
            Settings(**{**VALID_ENV, "DAILY_COST_LIMIT_USD": -5.0})


class TestThresholdRanges:
    """Threshold fields must be in [0.0, 1.0]."""

    def test_similarity_threshold_rejects_above_1(self):
        with pytest.raises(ValidationError, match="SIMILARITY_THRESHOLD"):
            Settings(**{**VALID_ENV, "SIMILARITY_THRESHOLD": 1.5})

    def test_similarity_threshold_rejects_negative(self):
        with pytest.raises(ValidationError, match="SIMILARITY_THRESHOLD"):
            Settings(**{**VALID_ENV, "SIMILARITY_THRESHOLD": -0.1})

    def test_cache_similarity_threshold_rejects_above_1(self):
        with pytest.raises(ValidationError, match="CACHE_SIMILARITY_THRESHOLD"):
            Settings(**{**VALID_ENV, "CACHE_SIMILARITY_THRESHOLD": 2.0})

    def test_guardrail_injection_threshold_rejects_above_1(self):
        with pytest.raises(ValidationError, match="GUARDRAIL_INJECTION_THRESHOLD"):
            Settings(**{**VALID_ENV, "GUARDRAIL_INJECTION_THRESHOLD": 1.1})


class TestEnumValidation:
    """Enum-like fields must only accept valid values."""

    def test_env_rejects_invalid_value(self):
        with pytest.raises(ValidationError, match="ENV"):
            Settings(**{**VALID_ENV, "ENV": "staging"})

    def test_env_accepts_production(self):
        s = Settings(**{**VALID_ENV, "ENV": "production"})
        assert s.ENV == "production"

    def test_env_accepts_testing(self):
        s = Settings(**{**VALID_ENV, "ENV": "testing"})
        assert s.ENV == "testing"

    def test_log_level_rejects_invalid(self):
        with pytest.raises(ValidationError, match="LOG_LEVEL"):
            Settings(**{**VALID_ENV, "LOG_LEVEL": "verbose"})

    def test_log_level_accepts_debug(self):
        s = Settings(**{**VALID_ENV, "LOG_LEVEL": "debug"})
        assert s.LOG_LEVEL == "debug"

    def test_guardrail_pii_mode_rejects_invalid(self):
        with pytest.raises(ValidationError, match="GUARDRAIL_PII_MODE"):
            Settings(**{**VALID_ENV, "GUARDRAIL_PII_MODE": "invalid"})

    def test_guardrail_pii_mode_accepts_redact(self):
        s = Settings(**{**VALID_ENV, "GUARDRAIL_PII_MODE": "redact"})
        assert s.GUARDRAIL_PII_MODE == "redact"

    def test_mcp_transport_rejects_invalid(self):
        with pytest.raises(ValidationError, match="MCP_TRANSPORT"):
            Settings(**{**VALID_ENV, "MCP_TRANSPORT": "grpc"})


class TestValidConfig:
    """A full valid config must load without errors."""

    def test_full_valid_config_loads(self):
        full = {
            **VALID_ENV,
            "HOST": "0.0.0.0",
            "PORT": 8008,
            "ENV": "development",
            "API_KEYS": "dev-key-1",
            "LOG_LEVEL": "info",
            "DEFAULT_MODEL": "openai/gpt-4o-mini",
            "EMBEDDING_MODEL": "openai/text-embedding-3-small",
            "CHUNK_SIZE": 512,
            "CHUNK_OVERLAP": 50,
            "RETRIEVAL_TOP_K": 10,
            "RERANK_TOP_N": 5,
            "SIMILARITY_THRESHOLD": 0.7,
            "GUARDRAIL_INJECTION_THRESHOLD": 0.8,
            "GUARDRAIL_PII_MODE": "flag",
            "CACHE_SIMILARITY_THRESHOLD": 0.95,
            "CACHE_TTL_HOURS": 24,
            "MAX_TOOL_CALLS_PER_TURN": 5,
            "MOCK_LLM": False,
            "DAILY_COST_LIMIT_USD": 10.00,
            "MCP_SERVER_PORT": 3001,
            "MCP_TRANSPORT": "stdio",
        }
        s = Settings(**full)
        assert s.DATABASE_URL == VALID_ENV["DATABASE_URL"]
        assert s.OPENROUTER_API_KEY == "sk-or-v1-test-key"
        assert s.CHUNK_SIZE == 512


class TestEnvironmentProfiles:
    """Computed properties differentiate development / production / testing."""

    def test_is_production_true_when_env_production(self):
        s = Settings(**{**VALID_ENV, "ENV": "production"})
        assert s.is_production is True

    def test_is_production_false_when_env_development(self):
        s = Settings(**VALID_ENV)  # default ENV=development
        assert s.is_production is False

    def test_is_testing_true_when_env_testing(self):
        s = Settings(**{**VALID_ENV, "ENV": "testing"})
        assert s.is_testing is True

    def test_is_testing_false_when_env_production(self):
        s = Settings(**{**VALID_ENV, "ENV": "production"})
        assert s.is_testing is False

    def test_debug_true_when_env_development(self):
        s = Settings(**VALID_ENV)  # default ENV=development
        assert s.debug is True

    def test_debug_false_when_env_production(self):
        s = Settings(**{**VALID_ENV, "ENV": "production"})
        assert s.debug is False
