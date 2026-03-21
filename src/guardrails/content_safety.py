"""Content safety checking via keyword patterns.

Detects hate speech, violence, and sexual content using keyword
patterns. Provides a testable ``_call_llm_judge`` seam for future
LLM-as-judge integration.

Usage::

    from src.guardrails.content_safety import check_content_safety

    result = check_content_safety("Some user text to check")
"""

from __future__ import annotations

import re
from typing import Any

import structlog

from src.guardrails.pipeline import GuardrailFlag, GuardrailResult

logger = structlog.get_logger(__name__)

# Content safety patterns: (category, compiled_regex, severity)
_SAFETY_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "hate_speech",
        re.compile(
            r"\b(ethnic\s+group.*(?:eliminate|destroy|eradicate|exterminate))|"
            r"((?:eliminate|destroy|eradicate|exterminate).*ethnic\s+group)|"
            r"(racial\s+(?:superiority|inferiority))|"
            r"(genocide|ethnic\s+cleansing)\b",
            re.IGNORECASE,
        ),
        "high",
    ),
    (
        "violence",
        re.compile(
            r"\b(?:how\s+to\s+(?:build\s+a\s+bomb|make\s+(?:a\s+)?(?:weapon|explosive|poison)))|"
            r"(?:(?:kill|murder|assassinate)\s+(?:people|someone|everyone))|"
            r"(?:mass\s+(?:shooting|murder|casualty))\b",
            re.IGNORECASE,
        ),
        "high",
    ),
    (
        "sexual_content",
        re.compile(
            r"\b(?:explicit\s+sexual|pornograph(?:y|ic)|sexual\s+exploitation)\b",
            re.IGNORECASE,
        ),
        "high",
    ),
]


def _call_llm_judge(text: str) -> dict[str, Any] | None:
    """Seam for LLM-as-judge safety evaluation.

    Returns None by default; override in tests or when LLM judge
    integration is wired.
    """
    return None


def check_content_safety(text: str) -> GuardrailResult:
    """Check text for unsafe content using keyword patterns.

    Args:
        text: Text to check for safety violations.

    Returns:
        GuardrailResult with pass/fail and category flags.
    """
    if not text or not text.strip():
        return GuardrailResult(passed=True)

    flags: list[GuardrailFlag] = []

    for category, pattern, severity in _SAFETY_PATTERNS:
        if pattern.search(text):
            flags.append(
                GuardrailFlag(
                    type="content_safety",
                    severity=severity,
                    detail=f"Unsafe content detected: {category}",
                )
            )

    if flags:
        logger.warning("content_safety_violation", categories=[f.detail for f in flags])
        return GuardrailResult(passed=False, flags=flags)

    return GuardrailResult(passed=True)
