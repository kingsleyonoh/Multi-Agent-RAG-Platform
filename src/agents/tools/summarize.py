"""Document summarization tool for agents.

Summarizes content by calling the LLM with a summarization prompt.

Usage::

    from src.agents.tools.summarize import summarize
    summary = await summarize(content="Long document text...")
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

# ── Module-level state (set by init_summarize at startup) ────────

_settings = None


def init_summarize(settings) -> None:
    """Wire summarize to a live LLM via routed_chat_completion.

    Called once at app startup from ``main.py`` lifespan.
    """
    global _settings
    _settings = settings
    logger.info("summarize_tool_initialized")


async def _call_llm(content: str) -> str:
    """Call LLM for summarization.

    Uses ``routed_chat_completion`` with task_type="summarization"
    when wired. Falls back to a length-based placeholder otherwise.
    """
    if _settings is None:
        logger.debug("summarize_not_wired")
        return f"Summary of {len(content)} characters of content."

    from src.llm.router import routed_chat_completion

    result = await routed_chat_completion(
        messages=[
            {
                "role": "system",
                "content": "Summarize the following text concisely. "
                "Return only the summary, no preamble.",
            },
            {"role": "user", "content": content},
        ],
        task_type="summarization",
        settings=_settings,
    )
    return result.content


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
