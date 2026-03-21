"""Long-term memory — summarise older messages for continuity.

Uses an LLM (via ``_call_llm`` seam) to summarise messages that have
fallen outside the short-term window.

Usage::

    from src.memory.long_term import LongTermMemory

    ltm = LongTermMemory()
    summary = ltm.summarize(old_messages)
    ltm.store_summary("conv_id", summary)
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class LongTermMemory:
    """Summarise and store older conversation messages."""

    def __init__(self) -> None:
        self._summaries: dict[str, str] = {}

    # ── Testable seam ────────────────────────────────────────────────

    @staticmethod
    def _call_llm(prompt: str) -> str:
        """Seam for LLM summarisation calls.

        Override in tests or wire to real provider.
        Returns a simple extractive summary by default.
        """
        # Default: concatenate first 200 chars of each message
        return prompt[:500] if prompt else ""

    # ── Public API ───────────────────────────────────────────────────

    def summarize(self, messages: list[Any]) -> str:
        """Summarise a list of messages into a short text.

        Args:
            messages: Messages to summarise.

        Returns:
            Summary string (empty string if no messages).
        """
        if not messages:
            return ""

        # Build a flat transcript for the LLM
        transcript = "\n".join(
            f"{getattr(m, 'role', 'unknown')}: {getattr(m, 'content', str(m))}"
            for m in messages
        )

        prompt = f"Summarize this conversation concisely:\n\n{transcript}"
        summary = self._call_llm(prompt)
        logger.debug("long_term_summarized", message_count=len(messages))
        return summary

    def store_summary(self, conversation_id: str, summary: str) -> None:
        """Store a summary keyed by conversation ID.

        Args:
            conversation_id: Unique conversation identifier.
            summary: Summary text to store.
        """
        self._summaries[conversation_id] = summary

    def get_summary(self, conversation_id: str) -> str | None:
        """Retrieve a stored summary.

        Args:
            conversation_id: Conversation to look up.

        Returns:
            Summary string or None if not found.
        """
        return self._summaries.get(conversation_id)
