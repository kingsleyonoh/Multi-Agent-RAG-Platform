"""OpenRouter LLM client.

OpenAI-compatible REST client for chat completions via OpenRouter.

Usage::

    from src.llm.openrouter import chat_completion

    result = await chat_completion(
        messages=[{"role": "user", "content": "Hello"}],
        model="openai/gpt-4o-mini",
        settings=app_settings,
    )
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ChatResult:
    """Response from an LLM chat completion."""

    content: str
    model_used: str
    tokens_in: int
    tokens_out: int
    cost_usd: float


async def chat_completion(
    *,
    messages: list[dict],
    model: str,
    settings: object,
    temperature: float = 0.7,
) -> ChatResult:
    """Send a chat completion request to OpenRouter.

    Args:
        messages: OpenAI-format message list.
        model: Model identifier (e.g. ``openai/gpt-4o-mini``).
        settings: App settings with ``OPENROUTER_*`` fields.
        temperature: Sampling temperature.

    Returns:
        :class:`ChatResult` with content and usage metadata.

    Raises:
        RuntimeError: On API error (with specific error types).
    """
    url = f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            url,
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
            },
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
        usage = data.get("usage", {})
        return ChatResult(
            content=choice["message"]["content"],
            model_used=data.get("model", model),
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            cost_usd=0.0,  # OpenRouter provides this via headers
        )
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected LLM response shape: {exc}") from exc
