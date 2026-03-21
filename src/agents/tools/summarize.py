"""Document summarization tool for agents.

Summarizes content by calling the LLM with a summarization prompt.

Usage::

    from src.agents.tools.summarize import summarize
    summary = await summarize(content="Long document text...")
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


async def _call_llm(content: str) -> str:
    """Call LLM for summarization. Separated for testability.

    In production, this calls ``routed_chat_completion`` with task_type="summarization".
    """
    # Placeholder — requires settings and LLM wiring
    return f"Summary of {len(content)} characters of content."


async def summarize(*, content: str) -> str:
    """Summarize document content using the LLM.

    Args:
        content: Text content to summarize.

    Returns:
        Summary string from the LLM.
    """
    if not content or not content.strip():
        return "No content to summarize — empty document."

    logger.info("summarize_called", content_len=len(content))
    return await _call_llm(content)


# Tool metadata for registry
TOOL_NAME = "summarize"
TOOL_DESCRIPTION = "Summarize a document or text passage."
TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "Text content to summarize",
        },
    },
    "required": ["content"],
}
