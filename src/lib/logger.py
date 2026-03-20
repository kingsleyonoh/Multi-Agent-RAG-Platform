"""Structured logging configuration using structlog.

Provides JSON-formatted structured logging to stdout with async-safe
context propagation via Python's ``contextvars``.  This module is the
**single source of truth** for logging configuration — all other
modules MUST use ``get_logger`` instead of ``logging.getLogger``.

Usage::

    from src.lib.logger import setup_logging, get_logger, bind_context

    # Once at startup (in main.py lifespan):
    setup_logging(json_output=True, log_level="INFO")

    # In any module:
    logger = get_logger(__name__)
    logger.info("document_ingested", doc_id="abc", pages=5)

    # Per-request context (in middleware):
    bind_context(request_id="req-123", user_id="user-456")
"""

from __future__ import annotations

import logging
import sys
from typing import IO, Any

import structlog
from structlog.contextvars import (
    bind_contextvars,
    clear_contextvars,
    merge_contextvars,
)


def setup_logging(
    *,
    json_output: bool = True,
    log_level: str = "INFO",
    _output: IO[str] | None = None,
) -> None:
    """Configure structlog processors and stdlib logging bridge.

    Call once during application startup.  Subsequent calls reconfigure
    (useful for tests that need different renderers).

    Args:
        json_output: ``True`` for JSON lines (production), ``False``
            for coloured console output (development).
        log_level: Root log level (DEBUG / INFO / WARNING / ERROR).
        _output: Internal override for the output stream. Defaults to
            ``sys.stdout``.  Used by tests to capture output.
    """
    output = _output if _output is not None else sys.stdout

    shared_processors: list[structlog.types.Processor] = [
        merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    if json_output:
        formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )
    else:
        formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(),
            ],
        )

    # Create a handler that writes to the chosen stream.
    handler = logging.StreamHandler(output)
    handler.setFormatter(formatter)

    # Configure stdlib root logger so third-party libs also route
    # through structlog processors.
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(module: str) -> structlog.stdlib.BoundLogger:
    """Return a logger pre-bound with ``module`` context.

    Args:
        module: Dotted module path, typically ``__name__``.

    Returns:
        A structlog ``BoundLogger`` with the ``module`` key set.
    """
    return structlog.get_logger(module=module)


def bind_context(**kwargs: Any) -> None:
    """Bind key-value pairs to the async-safe structlog context.

    Bound values appear in **all** subsequent log entries within the
    same asyncio task / thread until :func:`clear_context` is called.
    Typical keys: ``request_id``, ``user_id``.
    """
    bind_contextvars(**kwargs)


def clear_context() -> None:
    """Remove all previously bound context variables."""
    clear_contextvars()
