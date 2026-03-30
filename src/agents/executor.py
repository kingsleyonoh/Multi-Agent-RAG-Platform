"""ReAct-loop agent executor.

Implements the Reasoning + Acting loop that allows an LLM to
iteratively call tools and synthesize a final answer.

Usage::

    from src.agents.executor import AgentExecutor, ExecutorResult
    from src.agents.registry import ToolRegistry

    executor = AgentExecutor(
        registry=registry, settings=settings, max_steps=5,
    )
    result = await executor.run(user_message="...", system_prompt="...")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.llm.openrouter import ChatResult, chat_completion

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class ExecutorResult:
    """Result of an agent executor run.

    Attributes:
        answer: Final text answer from the LLM.
        tool_calls: List of tool call records (name, args, result).
        total_steps: Number of LLM iterations taken.
        model_used: Model that produced the final answer.
        tokens_in: Total prompt tokens across all steps.
        tokens_out: Total completion tokens across all steps.
        cost_usd: Total estimated cost across all steps.
    """

    answer: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    total_steps: int = 0
    model_used: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


class AgentExecutor:
    """ReAct-loop executor for multi-step agent reasoning.

    Sends messages to the LLM, executes tool calls from the response,
    feeds results back, and repeats until the LLM provides a final
    text answer or max_steps is reached.

    Args:
        registry: ToolRegistry containing allowed tools.
        settings: App settings (passed to chat_completion).
        max_steps: Maximum number of LLM iterations.
    """

    def __init__(
        self, registry, *, settings: object, max_steps: int = 5,
    ) -> None:
        self._registry = registry
        self._settings = settings
        self._max_steps = max_steps

    async def run(
        self,
        *,
        user_message: str,
        system_prompt: str,
        model: str = "openai/gpt-4o-mini",
    ) -> ExecutorResult:
        """Execute the ReAct loop.

        Args:
            user_message: The user's input message.
            system_prompt: System prompt for the LLM.
            model: Model identifier for routing.

        Returns:
            ExecutorResult with the final answer and tool call history.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        tools_schema = self._registry.to_openai_tools()
        tool_call_log: list[dict[str, Any]] = []
        steps = 0
        total_in = 0
        total_out = 0
        total_cost = 0.0
        last_model = model

        for step in range(self._max_steps):
            steps += 1
            logger.info("executor_step", step=step + 1, max=self._max_steps)

            result: ChatResult = await chat_completion(
                messages=messages,
                model=model,
                settings=self._settings,
                tools=tools_schema if tools_schema else None,
            )

            total_in += result.tokens_in
            total_out += result.tokens_out
            total_cost += result.cost_usd
            last_model = result.model_used

            # If no tool calls, we have a final answer
            if not result.tool_calls:
                return ExecutorResult(
                    answer=result.content or "",
                    tool_calls=tool_call_log,
                    total_steps=steps,
                    model_used=last_model,
                    tokens_in=total_in,
                    tokens_out=total_out,
                    cost_usd=total_cost,
                )

            # Process each tool call
            messages.append(result.raw_message)

            for tc in result.tool_calls:
                func_name = tc["function"]["name"]
                call_id = tc["id"]

                try:
                    func_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    func_args = {}

                # Whitelist check
                if not self._registry.is_whitelisted(func_name):
                    result_str = (
                        f"Error: Tool '{func_name}' is not registered. "
                        f"Available tools: {self._registry.list_tools()}"
                    )
                    logger.warning(
                        "tool_not_whitelisted",
                        tool=func_name,
                        available=self._registry.list_tools(),
                    )
                else:
                    tool_spec = self._registry.get(func_name)
                    try:
                        tool_result = await tool_spec.handler(**func_args)
                        result_str = (
                            json.dumps(tool_result)
                            if not isinstance(tool_result, str)
                            else tool_result
                        )
                    except Exception as exc:
                        result_str = f"Error executing {func_name}: {exc}"
                        logger.error(
                            "tool_execution_error",
                            tool=func_name,
                            error=str(exc),
                        )

                tool_call_log.append({
                    "tool": func_name,
                    "args": func_args,
                    "result": result_str,
                })

                # Add tool result message for the LLM
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result_str,
                })

        # Exhausted max_steps
        logger.warning("executor_max_steps", steps=steps)
        return ExecutorResult(
            answer=(
                f"Reached max steps ({self._max_steps}). "
                "Could not produce a final answer."
            ),
            tool_calls=tool_call_log,
            total_steps=steps,
            model_used=last_model,
            tokens_in=total_in,
            tokens_out=total_out,
            cost_usd=total_cost,
        )
