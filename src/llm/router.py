"""Multi-model routing logic.

Routes tasks to appropriate LLM models based on task type,
with support for preferred model override and budget-based downgrade.

Usage::

    from src.llm.router import route_model, routed_chat_completion

    model = route_model(task_type="chat", settings=settings)
    result = await routed_chat_completion(
        messages=[{"role": "user", "content": "Hello"}],
        task_type="chat",
        settings=settings,
    )
"""

from __future__ import annotations

import structlog

from src.llm.openrouter import ChatResult, chat_completion

logger = structlog.get_logger(__name__)


# Task-type → model ID mapping
ROUTING_TABLE: dict[str, str] = {
    "chat": "openai/gpt-4o-mini",
    "summarization": "google/gemini-2.0-flash-exp",
    "evaluation": "openai/gpt-4o-mini",
    "embedding": "openai/text-embedding-3-small",
    "memory": "google/gemini-2.0-flash-exp",
}


def route_model(
    *,
    task_type: str,
    settings: object,
    preferred_model: str | None = None,
) -> str:
    """Resolve the model ID for a given task type.

    Args:
        task_type: One of the keys in ``ROUTING_TABLE``.
        settings: App settings with ``DEFAULT_MODEL``.
        preferred_model: If set, bypasses the routing table entirely.

    Returns:
        Model identifier string.
    """
    if preferred_model:
        logger.debug("model_routing_bypass", preferred=preferred_model)
        return preferred_model

    model = ROUTING_TABLE.get(
        task_type,
        getattr(settings, "DEFAULT_MODEL", "openai/gpt-4o-mini"),
    )
    logger.debug("model_routed", task_type=task_type, model=model)
    return model


async def routed_chat_completion(
    *,
    messages: list[dict],
    task_type: str,
    settings: object,
    preferred_model: str | None = None,
    temperature: float = 0.7,
) -> ChatResult:
    """Route to the correct model then call chat_completion.

    Args:
        messages: OpenAI-format message list.
        task_type: Task type for model routing.
        settings: App settings.
        preferred_model: Override model selection.
        temperature: Sampling temperature.

    Returns:
        :class:`ChatResult` from the resolved model.
    """
    model = route_model(
        task_type=task_type,
        settings=settings,
        preferred_model=preferred_model,
    )
    return await chat_completion(
        messages=messages,
        model=model,
        settings=settings,
        temperature=temperature,
    )
