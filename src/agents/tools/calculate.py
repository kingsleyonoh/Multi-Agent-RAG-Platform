"""Safe math evaluator tool for agents.

Evaluates mathematical expressions using AST parsing for safety.

Usage::

    from src.agents.tools.calculate import calculate
    result = await calculate(expression="2 + 3 * 4")
"""

from __future__ import annotations

import ast
import operator
from typing import Union

import structlog

logger = structlog.get_logger(__name__)

# Allowed binary operators
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Allowed unary operators
_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Blocked patterns — reject before parsing
_BLOCKED_KEYWORDS = {
    "__import__", "exec", "eval", "open", "compile",
    "getattr", "setattr", "delattr", "globals", "locals",
    "breakpoint", "input", "print",
}


def _safe_eval(node: ast.AST) -> Union[int, float]:
    """Recursively evaluate an AST node safely.

    Only allows numeric literals and basic arithmetic operators.

    Raises:
        ValueError: On any unsupported node type.
    """
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.BinOp):
        op_func = _OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsafe operator: {type(node.op).__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return op_func(left, right)

    if isinstance(node, ast.UnaryOp):
        op_func = _UNARY_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsafe unary operator: {type(node.op).__name__}")
        return op_func(_safe_eval(node.operand))

    raise ValueError(f"Unsafe expression node: {type(node).__name__}")


async def calculate(*, expression: str) -> Union[int, float]:
    """Safely evaluate a mathematical expression.

    Args:
        expression: Math expression string (e.g. ``"2 + 3 * 4"``).

    Returns:
        Numeric result.

    Raises:
        ValueError: If expression contains unsafe operations or is invalid.
    """
    # Pre-check for blocked keywords
    expr_lower = expression.lower()
    for keyword in _BLOCKED_KEYWORDS:
        if keyword in expr_lower:
            raise ValueError(f"Unsafe expression: contains blocked keyword '{keyword}'")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid expression: {exc}") from exc

    logger.debug("calculate_called", expression=expression[:100])
    return _safe_eval(tree)


# Tool metadata for registry
TOOL_NAME = "calculate"
TOOL_DESCRIPTION = "Evaluate a mathematical expression safely."
TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "expression": {
            "type": "string",
            "description": "Mathematical expression to evaluate",
        },
    },
    "required": ["expression"],
}
