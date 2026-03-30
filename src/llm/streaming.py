"""SSE streaming wrapper for LLM chat completions.

Provides an async generator that yields Server-Sent Events from
OpenRouter's streaming API.

Usage::

    from src.llm.streaming import stream_chat_completion, format_sse

    async for event in stream_chat_completion(messages=msgs, model=m, settings=s):
        yield format_sse(event)
"""

from __future__ import annotations

import json

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def _stream_request(
    url: str, payload: dict, headers: dict,
) -> httpx.Response:
    """Make the streaming HTTP POST with retry on connection errors."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code >= 500:
        raise RuntimeError(f"LLM_PROVIDER_ERROR: Server error {resp.status_code}")
    return resp


def format_sse(data: dict) -> str:
    """Format a dict as an SSE-compatible ``data:`` line.

    Args:
        data: Event payload to serialize.

    Returns:
        SSE event string ending with double newline.
    """
    return f"data: {json.dumps(data)}\n\n"


async def stream_chat_completion(
    *,
    messages: list[dict],
    model: str,
    settings: object,
    temperature: float = 0.7,
) -> __import__("collections.abc", fromlist=["AsyncGenerator"]).AsyncGenerator:
    """Stream chat completion tokens as SSE events.

    Yields dicts with ``token`` (str) and ``done`` (bool) keys.
    On API error, yields a single ``{"error": ...}`` event.

    Args:
        messages: OpenAI-format message list.
        model: Model identifier.
        settings: App settings with ``OPENROUTER_*`` fields.
        temperature: Sampling temperature.

    Yields:
        Event dicts: ``{"token": str, "done": False}`` or ``{"done": True}``.
    """
    url = f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"

    try:
        resp = await _stream_request(
            url,
            payload={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            },
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "X-Title": getattr(settings, "OPENROUTER_APP_NAME", "rag-platform"),
                "HTTP-Referer": "https://github.com/multi-agent-rag-platform",
                "Content-Type": "application/json",
            },
        )

        if resp.status_code != 200:
            logger.error("stream_api_error", status=resp.status_code)
            yield {"error": f"LLM API failed with status {resp.status_code}", "done": True}
            return

        # Parse SSE lines from response body
        for line in resp.text.split("\n"):
            line = line.strip()
            if not line or not line.startswith("data: "):
                continue

            payload = line.removeprefix("data: ").strip()
            if payload == "[DONE]":
                yield {"done": True}
                return

            try:
                chunk = json.loads(payload)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield {"token": content, "done": False}
            except (json.JSONDecodeError, IndexError, KeyError) as exc:
                logger.warning("stream_parse_error", error=str(exc))
                continue

        # If we reach here without [DONE], signal completion
        yield {"done": True}

    except httpx.HTTPError as exc:
        logger.error("stream_connection_error", error=str(exc))
        yield {"error": f"Connection error: {exc}", "done": True}
