"""Short-term memory — sliding window of recent messages.

Keeps the last N messages in the context window for LLM calls.

Usage::

    from src.memory.short_term import ShortTermMemory

    stm = ShortTermMemory(window_size=20)
    recent = stm.get_context(all_messages)
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ShortTermMemory:
    """Sliding window memory over conversation messages.

    Args:
        window_size: Maximum number of messages to keep. Default 20.
    """

    def __init__(self, window_size: int = 20) -> None:
        self.window_size = window_size

    def get_context(self, messages: list[Any]) -> list[Any]:
        """Return the most recent messages up to window_size.

        Args:
            messages: Full list of conversation messages.

        Returns:
            Trimmed list of the most recent messages.
        """
        if not messages:
            return []

        if len(messages) <= self.window_size:
            return list(messages)

        trimmed = messages[-self.window_size :]
        logger.debug(
            "short_term_trimmed",
            original=len(messages),
            kept=len(trimmed),
        )
        return trimmed
