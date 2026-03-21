"""PII detection and redaction.

Scans text for personally identifiable information (SSN, credit card,
email, phone) using regex patterns. Supports three modes:

- ``flag``: detect + report, do not block
- ``block``: detect + block the request
- ``redact``: detect + replace PII with ``[REDACTED]``

Usage::

    from src.guardrails.pii import detect_pii

    result = detect_pii("My SSN is 123-45-6789", mode="redact")
    print(result.redacted_text)  # "My SSN is [REDACTED]"
"""

from __future__ import annotations

import re
from typing import Literal

import structlog

from src.guardrails.pipeline import GuardrailFlag, GuardrailResult

logger = structlog.get_logger(__name__)

# Each detector: (name, compiled_regex, flag_type)
_PII_DETECTORS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "SSN",
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "pii_ssn",
    ),
    (
        "Credit Card",
        re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        "pii_credit_card",
    ),
    (
        "Email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "pii_email",
    ),
    (
        "Phone",
        re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "pii_phone",
    ),
]


def detect_pii(
    text: str,
    mode: Literal["flag", "block", "redact"] = "flag",
) -> GuardrailResult:
    """Scan text for PII patterns.

    Args:
        text: Input text to scan.
        mode: ``flag`` (report only), ``block`` (reject), ``redact`` (mask).

    Returns:
        GuardrailResult with flags and optional ``redacted_text``.
    """
    if not text or not text.strip():
        return GuardrailResult(passed=True)

    flags: list[GuardrailFlag] = []
    redacted = text

    for name, pattern, flag_type in _PII_DETECTORS:
        matches = pattern.findall(text)
        if matches:
            flags.append(
                GuardrailFlag(
                    type=flag_type,
                    severity="high",
                    detail=f"{name} detected ({len(matches)} occurrence(s))",
                )
            )
            if mode == "redact":
                redacted = pattern.sub("[REDACTED]", redacted)

    if not flags:
        return GuardrailResult(passed=True)

    if mode == "block":
        logger.warning("pii_blocked", types=[f.type for f in flags])
        return GuardrailResult(passed=False, flags=flags)

    if mode == "redact":
        logger.info("pii_redacted", types=[f.type for f in flags])
        return GuardrailResult(passed=True, flags=flags, redacted_text=redacted)

    # flag mode — report but pass
    logger.info("pii_flagged", types=[f.type for f in flags])
    return GuardrailResult(passed=True, flags=flags)
