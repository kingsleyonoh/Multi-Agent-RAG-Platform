"""OpenRouter LLM client.

OpenAI-compatible REST client for chat completions via OpenRouter.
Supports both standard completions and tool-calling (function calling).

Usage::

    from src.llm.openrouter import chat_completion

    result = await chat_completion(
        messages=[{"role": "user", "content": "Hello"}],
        model="openai/gpt-4o-mini",
        settings=app_settings,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_message,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


def _is_retryable_error(error: BaseException) -> bool:
    """Return True for transient errors that should be retried."""
    msg = str(error)
    # Retry rate limits and server errors, NOT client errors (402, 400)
    return "RATE_LIMITED" in msg or "LLM_PROVIDER_ERROR" in msg


_llm_retry = retry(
    retry=retry_if_exception_message(match=r"RATE_LIMITED|LLM_PROVIDER_ERROR"),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)


@dataclass(frozen=True, slots=True)
class ChatResult:
    """Response from an LLM chat completion.

    Attributes:
        content: Text content of the response (may be None for tool calls).
        model_used: Model identifier that served the request.
        tokens_in: Prompt token count.
        tokens_out: Completion token count.
        cost_usd: Estimated cost in USD.
        tool_calls: Raw tool_calls list from the API (None if no tools).
        raw_message: Full message dict from the API response.
    """

    content: str | None
    model_used: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    tool_calls: list[dict[str, Any]] | None = field(default=None)
    raw_message: dict[str, Any] = field(default_factory=dict)


@_llm_retry
async def chat_completion(
    *,
    messages: list[dict],
    model: str,
    settings: object,
    temperature: float = 0.7,
    tools: list[dict] | None = None,
) -> ChatResult:
    """Send a chat completion request to OpenRouter.

    Args:
        messages: OpenAI-format message list.
        model: Model identifier (e.g. ``openai/gpt-4o-mini``).
        settings: App settings with ``OPENROUTER_*`` fields.
        temperature: Sampling temperature.
        tools: Optional list of tool definitions (OpenAI format).

    Returns:
        :class:`ChatResult` with content, usage metadata, and tool calls.

    Raises:
        RuntimeError: On API error (with specific error types).
    """
    url = f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "X-Title": getattr(settings, "OPENROUTER_APP_NAME", "rag-platform"),
                "HTTP-Referer": "https://github.com/multi-agent-rag-platform",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code == 429:
        raise RuntimeError("RATE_LIMITED: Too many requests — retry with backoff")
    if resp.status_code == 402:
        raise RuntimeError("COST_LIMIT_EXCEEDED: Insufficient credits")
    if resp.status_code >= 500:
        raise RuntimeError(f"LLM_PROVIDER_ERROR: Server error {resp.status_code}")
    if resp.status_code != 200:
        logger.error("llm_api_error", status=resp.status_code, body=resp.text[:500])
        raise RuntimeError(f"LLM API failed with status {resp.status_code}")

    data = resp.json()
    try:
        choice = data["choices"][0]
        message = choice["message"]
        usage = data.get("usage", {})
        return ChatResult(
            content=message.get("content"),
            model_used=data.get("model", model),
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            cost_usd=0.0,  # OpenRouter provides this via headers
            tool_calls=message.get("tool_calls"),
            raw_message=message,
        )
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected LLM response shape: {exc}") from exc
