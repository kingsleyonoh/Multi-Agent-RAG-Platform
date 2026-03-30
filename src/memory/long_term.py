"""Long-term memory — summarise older messages for continuity.

Uses an LLM (via ``_call_llm`` seam) to summarise messages that have
fallen outside the short-term window.

Usage::

    from src.memory.long_term import LongTermMemory

    ltm = LongTermMemory()
    summary = await ltm.summarize(old_messages)
    ltm.store_summary("conv_id", summary)
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class LongTermMemory:
    """Summarise and store older conversation messages."""

    def __init__(self, *, settings=None) -> None:
        self._summaries: dict[str, str] = {}
        self._settings = settings

    # ── Testable seam ────────────────────────────────────────────────

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM for summarisation.

        Uses ``routed_chat_completion`` when settings are available.
        Falls back to truncated prompt otherwise.
        """
        if self._settings is None:
            return prompt[:500] if prompt else ""

        from src.llm.router import routed_chat_completion

        result = await routed_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            task_type="summarization",
            settings=self._settings,
        )
        return result.content

    # ── Public API ───────────────────────────────────────────────────

    async def summarize(self, messages: list[Any]) -> str:
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
        summary = await self._call_llm(prompt)
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
