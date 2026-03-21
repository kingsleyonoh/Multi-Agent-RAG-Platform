"""Prompt injection detection via pattern matching.

Scores text 0.0–1.0 based on how many injection patterns match.
Blocks if score exceeds the configurable threshold (default 0.8).

Usage::

    from src.guardrails.injection import detect_injection

    result = detect_injection("Ignore all previous instructions")
    if not result.passed:
        print("Injection detected!", result.score)
"""

from __future__ import annotations

import re

import structlog

from src.guardrails.pipeline import GuardrailFlag, GuardrailResult

logger = structlog.get_logger(__name__)

# Patterns that indicate prompt injection attempts.
# Each tuple: (compiled_regex, weight, description)
_INJECTION_PATTERNS: list[tuple[re.Pattern[str], float, str]] = [
    (
        re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|rules)", re.IGNORECASE),
        1.0,
        "Ignore previous instructions",
    ),
    (
        re.compile(r"you\s+are\s+now\s+\w+", re.IGNORECASE),
        0.9,
        "Role override (you are now X)",
    ),
    (
        re.compile(r"\bDAN\b.*can\s+do\s+anything", re.IGNORECASE),
        1.0,
        "DAN jailbreak pattern",
    ),
    (
        re.compile(r"(show|reveal|display|print|tell)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions)", re.IGNORECASE),
        0.9,
        "System prompt extraction",
    ),
    (
        re.compile(r"(forget|disregard|override)\s+(everything|all|your)\s*(instructions|rules|guidelines)?", re.IGNORECASE),
        1.0,
        "Instruction override",
    ),
    (
        re.compile(r"do\s+not\s+follow\s+(your|any)\s+(rules|guidelines|instructions)", re.IGNORECASE),
        1.0,
        "Rule bypass",
    ),
    (
        re.compile(r"act\s+as\s+(if\s+)?(you\s+(are|were)\s+)?(a|an)?\s*(unrestricted|unfiltered|uncensored)", re.IGNORECASE),
        0.9,
        "Unrestricted mode request",
    ),
    (
        re.compile(r"pretend\s+(you\s+)?(are|have)\s+no\s+(restrictions|filters|guidelines)", re.IGNORECASE),
        0.9,
        "Pretend no restrictions",
    ),
]


def detect_injection(
    text: str,
    *,
    threshold: float = 0.8,
) -> GuardrailResult:
    """Detect prompt injection attempts in user input.

    Args:
        text: The user's input text.
        threshold: Score above which input is blocked (0.0-1.0).

    Returns:
        GuardrailResult with score and pass/fail status.
    """
    if not text or not text.strip():
        return GuardrailResult(passed=True, score=0.0)

    matched_flags: list[GuardrailFlag] = []
    max_weight = 0.0

    for pattern, weight, description in _INJECTION_PATTERNS:
        if pattern.search(text):
            matched_flags.append(
                GuardrailFlag(
                    type="injection",
                    severity="high",
                    detail=description,
                )
            )
            max_weight = max(max_weight, weight)

    # Score is the highest weight among matches
    score = max_weight
    passed = score <= threshold

    if not passed:
        logger.warning(
            "injection_detected",
            score=score,
            patterns=[f.detail for f in matched_flags],
        )

    return GuardrailResult(passed=passed, flags=matched_flags, score=score)
