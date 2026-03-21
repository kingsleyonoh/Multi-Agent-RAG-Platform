"""Conversation summary job.

Finds conversations that exceed the memory window threshold and
generates summaries for the older messages.

Designed to run every 6 hours via a scheduler.

Usage::

    from src.jobs.conversation_summary import summarize_long_conversations

    results = summarize_long_conversations(conversations, threshold=20)
"""

from __future__ import annotations

from typing import Any


def summarize_long_conversations(
    conversations: dict[str, list[Any]],
    *,
    threshold: int = 20,
) -> dict[str, str]:
    """Summarize conversations exceeding *threshold* messages.

    Args:
        conversations: Mapping of session_id → list of messages.
        threshold: Message count above which a summary is generated.

    Returns:
        Mapping of session_id → summary string for conversations that
        exceeded the threshold.
    """
    results: dict[str, str] = {}
    for session_id, messages in conversations.items():
        if len(messages) > threshold:
            # Seam: in production, call an LLM to generate the summary.
            results[session_id] = _generate_summary(messages, threshold)
    return results


def _generate_summary(messages: list[Any], threshold: int) -> str:
    """Seam — override in production to call LLM summarisation."""
    older = messages[: len(messages) - threshold]
    return f"Summary of {len(older)} older messages"
