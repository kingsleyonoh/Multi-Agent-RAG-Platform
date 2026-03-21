"""Unit tests for src/lib/logger — structured logging with structlog.

Tests cover: logger creation, JSON/console output format, context
propagation (bind/clear), log-level filtering, and setup configuration.
All tests capture structlog output via BytesIO / StringIO — no I/O needed.
"""

from __future__ import annotations

import json
import io
import logging

import pytest
import structlog

from src.lib.logger import setup_logging, get_logger, bind_context, clear_context


# ── Helpers ──────────────────────────────────────────────────────

def _capture_json_output(logger: structlog.BoundLogger, msg: str, **kw) -> dict:
    """Call logger.info and capture the JSON line from stdout."""
    sio = io.StringIO()
    # Temporarily redirect structlog's output
    import structlog._config as _cfg

    # We reconfigure with a custom file to capture output
    setup_logging(json_output=True, log_level="DEBUG", _output=sio)
    bound = get_logger(logger._context.get("module", "test"))
    bound.info(msg, **kw)
    sio.seek(0)
    line = sio.readline().strip()
    return json.loads(line)


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_structlog():
    """Reset structlog configuration and contextvars between tests."""
    clear_context()
    yield
    clear_context()
    structlog.reset_defaults()


# ── get_logger ───────────────────────────────────────────────────

class TestGetLogger:
    """Verify logger creation and module context."""

    def test_returns_bound_logger(self) -> None:
        """get_logger() returns a structlog BoundLogger instance."""
        setup_logging(json_output=True, log_level="INFO")
        logger = get_logger("mymodule")
        # structlog loggers are BoundLoggerLazyProxy or BoundLogger
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_includes_module_context(self) -> None:
        """Logger output includes 'module' key matching the argument."""
        sio = io.StringIO()
        setup_logging(json_output=True, log_level="DEBUG", _output=sio)
        logger = get_logger("src.db.postgres")
        logger.info("test_event")

        sio.seek(0)
        data = json.loads(sio.readline().strip())
        assert data["module"] == "src.db.postgres"


# ── Output format ────────────────────────────────────────────────

class TestOutputFormat:
    """Verify JSON and console rendering modes."""

    def test_json_output_format(self) -> None:
        """JSON renderer emits valid JSON with expected keys."""
        sio = io.StringIO()
        setup_logging(json_output=True, log_level="DEBUG", _output=sio)
        logger = get_logger("mod")
        logger.info("hello_world", extra_key="val")

        sio.seek(0)
        data = json.loads(sio.readline().strip())

        assert data["event"] == "hello_world"
        assert data["level"] == "info"
        assert "timestamp" in data
        assert data["module"] == "mod"
        assert data["extra_key"] == "val"

    def test_console_output_format(self) -> None:
        """Console renderer produces human-readable, non-JSON output."""
        sio = io.StringIO()
        setup_logging(json_output=False, log_level="DEBUG", _output=sio)
        logger = get_logger("mod")
        logger.info("hello_world")

        sio.seek(0)
        line = sio.readline().strip()

        # Console output should NOT be valid JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(line)
        # But should contain the event name
        assert "hello_world" in line


# ── Context propagation ─────────────────────────────────────────

class TestContextPropagation:
    """Verify bind_context / clear_context lifecycle."""

    def test_bind_context_adds_fields(self) -> None:
        """bind_context() adds fields to subsequent log entries."""
        sio = io.StringIO()
        setup_logging(json_output=True, log_level="DEBUG", _output=sio)

        bind_context(request_id="req-123", user_id="user-456")
        logger = get_logger("mod")
        logger.info("with_context")

        sio.seek(0)
        data = json.loads(sio.readline().strip())
        assert data["request_id"] == "req-123"
        assert data["user_id"] == "user-456"

    def test_clear_context_removes_fields(self) -> None:
        """clear_context() removes previously bound fields."""
        sio = io.StringIO()
        setup_logging(json_output=True, log_level="DEBUG", _output=sio)

        bind_context(request_id="req-999")
        clear_context()
        logger = get_logger("mod")
        logger.info("after_clear")

        sio.seek(0)
        data = json.loads(sio.readline().strip())
        assert "request_id" not in data


# ── Log levels ───────────────────────────────────────────────────

class TestLogLevels:
    """Verify level filtering."""

    def test_info_emits_at_info_level(self) -> None:
        """INFO messages emit when level is INFO."""
        sio = io.StringIO()
        setup_logging(json_output=True, log_level="INFO", _output=sio)
        logger = get_logger("mod")
        logger.info("visible")

        sio.seek(0)
        assert sio.readline().strip()  # non-empty = emitted

    def test_debug_suppressed_at_info_level(self) -> None:
        """DEBUG messages do NOT emit when level is INFO."""
        sio = io.StringIO()
        setup_logging(json_output=True, log_level="INFO", _output=sio)
        logger = get_logger("mod")
        logger.debug("invisible")

        sio.seek(0)
        assert sio.readline().strip() == ""  # empty = suppressed


# ── setup_logging ────────────────────────────────────────────────

class TestSetupLogging:
    """Verify one-time configuration."""

    def test_setup_logging_configures_without_error(self) -> None:
        """setup_logging() completes without raising."""
        setup_logging(json_output=True, log_level="WARNING")
        # If we get here, configuration succeeded
        logger = get_logger("test")
        assert logger is not None
