"""Shared guardrail types and input/output pipeline functions.

Provides the ``GuardrailResult`` and ``GuardrailFlag`` dataclasses used
across all guardrail modules, plus the topic-policy and token-budget
checks for the input pipeline.

Usage::

    from src.guardrails.pipeline import (
        GuardrailResult, GuardrailFlag,
        check_topic_policy, check_token_budget,
    )
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class GuardrailFlag:
    """A single guardrail finding."""

    type: str
    severity: str  # "low", "medium", "high"
    detail: str


@dataclass(slots=True)
class GuardrailResult:
    """Aggregated result from one or more guardrail checks."""

    passed: bool
    flags: list[GuardrailFlag] = field(default_factory=list)
    score: float = 0.0
    redacted_text: str | None = None


# ── Topic policy ─────────────────────────────────────────────────────

def check_topic_policy(
    text: str,
    denied_topics: list[str],
) -> GuardrailResult:
    """Check if text contains any denied topics.

    Args:
        text: User input text.
        denied_topics: List of topic keywords to deny.

    Returns:
        GuardrailResult with pass/fail and flags.
    """
    text_lower = text.lower()
    found: list[GuardrailFlag] = []

    for topic in denied_topics:
        if topic.lower() in text_lower:
            found.append(
                GuardrailFlag(
                    type="denied_topic",
                    severity="high",
                    detail=f"Denied topic detected: {topic}",
                )
            )

    passed = len(found) == 0
    if not passed:
        logger.warning("topic_policy_violation", topics=[f.detail for f in found])

    return GuardrailResult(passed=passed, flags=found)


# ── Token budget ─────────────────────────────────────────────────────

def check_token_budget(
    estimated_tokens: int,
    session_budget: int,
) -> GuardrailResult:
    """Check if estimated token usage exceeds session budget.

    Args:
        estimated_tokens: Estimated tokens for this request.
        session_budget: Remaining token budget for the session.

    Returns:
        GuardrailResult with pass/fail status.
    """
    if estimated_tokens <= session_budget:
        return GuardrailResult(passed=True)

    flag = GuardrailFlag(
        type="token_budget_exceeded",
        severity="high",
        detail=f"Estimated {estimated_tokens} tokens exceeds budget of {session_budget}",
    )
    logger.warning(
        "token_budget_exceeded",
        estimated=estimated_tokens,
        budget=session_budget,
    )
    return GuardrailResult(passed=False, flags=[flag])


# ── Source attribution ───────────────────────────────────────────────

_CITATION_PATTERN = re.compile(r"\[([^\]]+)\]")


def verify_source_attribution(
    response: str,
    source_ids: list[str],
) -> GuardrailResult:
    """Verify that cited sources exist in retrieval results.

    Uses regex to find ``[Source Name]`` citations and checks them
    against the provided source IDs.

    Args:
        response: LLM response text that may contain citations.
        source_ids: Valid source identifiers from retrieval.

    Returns:
        GuardrailResult with flags for invalid citations.
    """
    cited = _CITATION_PATTERN.findall(response)
    if not cited:
        return GuardrailResult(passed=True)

    flags: list[GuardrailFlag] = []
    source_set = set(source_ids)

    for cite in cited:
        if cite not in source_set:
            flags.append(
                GuardrailFlag(
                    type="invalid_citation",
                    severity="medium",
                    detail=f"Cited source not found: {cite}",
                )
            )

    if flags:
        logger.warning("invalid_citations", count=len(flags))

    return GuardrailResult(passed=True, flags=flags)


# ── Input pipeline ───────────────────────────────────────────────────

def run_input_guardrails(
    text: str,
    denied_topics: list[str],
    injection_threshold: float = 0.8,
    pii_mode: str = "flag",
) -> GuardrailResult:
    """Run the full input guardrail pipeline.

    Chains injection detection → PII detection → topic policy.
    Short-circuits on any blocking failure.

    Args:
        text: Raw user input.
        denied_topics: Topics to deny.
        injection_threshold: Score threshold for injection blocking.
        pii_mode: PII handling mode ("flag", "block", "redact").

    Returns:
        Aggregated GuardrailResult.
    """
    from src.guardrails.injection import detect_injection
    from src.guardrails.pii import detect_pii

    all_flags: list[GuardrailFlag] = []

    # 1. Injection detection
    inj_result = detect_injection(text, threshold=injection_threshold)
    all_flags.extend(inj_result.flags)
    if not inj_result.passed:
        return GuardrailResult(passed=False, flags=all_flags)

    # 2. PII detection
    pii_result = detect_pii(text, mode=pii_mode)
    all_flags.extend(pii_result.flags)
    if not pii_result.passed:
        return GuardrailResult(passed=False, flags=all_flags)

    # 3. Topic policy
    topic_result = check_topic_policy(text, denied_topics)
    all_flags.extend(topic_result.flags)
    if not topic_result.passed:
        return GuardrailResult(passed=False, flags=all_flags)

    return GuardrailResult(
        passed=True,
        flags=all_flags,
        redacted_text=pii_result.redacted_text,
    )


# ── Output pipeline ──────────────────────────────────────────────────

def run_output_guardrails(
    response: str,
    source_chunks: list[str],
    source_ids: list[str],
) -> GuardrailResult:
    """Run the full output guardrail pipeline.

    Chains content safety → hallucination detection → source attribution.

    Args:
        response: LLM-generated response.
        source_chunks: Retrieved source chunk texts.
        source_ids: Valid source identifiers.

    Returns:
        Aggregated GuardrailResult.
    """
    from src.guardrails.content_safety import check_content_safety
    from src.guardrails.hallucination import detect_hallucination

    all_flags: list[GuardrailFlag] = []

    # 1. Content safety (blocks)
    safety = check_content_safety(response)
    all_flags.extend(safety.flags)
    if not safety.passed:
        return GuardrailResult(passed=False, flags=all_flags)

    # 2. Hallucination detection (informational)
    hall = detect_hallucination(response, source_chunks)
    all_flags.extend(hall.flags)

    # 3. Source attribution (informational)
    attr = verify_source_attribution(response, source_ids)
    all_flags.extend(attr.flags)

    return GuardrailResult(passed=True, flags=all_flags)
