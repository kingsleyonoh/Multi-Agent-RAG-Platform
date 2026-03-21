"""Hallucination detection by comparing response against source chunks.

Uses sentence-level overlap to identify claims that have no backing in
the retrieved source material.

Usage::

    from src.guardrails.hallucination import detect_hallucination

    result = detect_hallucination(
        response="Python was created by James Gosling.",
        source_chunks=["Python was created by Guido van Rossum in 1991."],
    )
"""

from __future__ import annotations

import re

import structlog

from src.guardrails.pipeline import GuardrailFlag, GuardrailResult

logger = structlog.get_logger(__name__)

# Minimum word overlap ratio to consider a sentence grounded.
_GROUNDING_THRESHOLD = 0.4


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences by common delimiters."""
    sentences = re.split(r"[.!?]+", text)
    return [s.strip() for s in sentences if s.strip() and len(s.split()) >= 3]


def _word_overlap(sentence: str, source: str) -> float:
    """Compute the fraction of words in sentence found in source."""
    sent_words = set(sentence.lower().split())
    src_words = set(source.lower().split())
    if not sent_words:
        return 1.0
    return len(sent_words & src_words) / len(sent_words)


def detect_hallucination(
    response: str,
    source_chunks: list[str],
) -> GuardrailResult:
    """Detect hallucinated claims in a response.

    Splits the response into sentences. For each sentence, checks
    word-level overlap against all source chunks. Sentences with
    overlap below ``_GROUNDING_THRESHOLD`` across ALL chunks are
    flagged as potential hallucinations.

    Args:
        response: The LLM-generated response text.
        source_chunks: List of source chunk texts from retrieval.

    Returns:
        GuardrailResult with flags for ungrounded sentences.
    """
    if not response or not response.strip():
        return GuardrailResult(passed=True)

    sentences = _split_sentences(response)
    if not sentences:
        return GuardrailResult(passed=True)

    flags: list[GuardrailFlag] = []
    combined_source = " ".join(source_chunks) if source_chunks else ""

    for sentence in sentences:
        if not source_chunks:
            # No sources → everything is ungrounded
            flags.append(
                GuardrailFlag(
                    type="hallucination",
                    severity="medium",
                    detail=f"No sources to verify: {sentence[:80]}",
                )
            )
            continue

        # Check overlap with each source chunk, take the max
        best_overlap = max(
            _word_overlap(sentence, chunk) for chunk in source_chunks
        )

        if best_overlap < _GROUNDING_THRESHOLD:
            flags.append(
                GuardrailFlag(
                    type="hallucination",
                    severity="medium",
                    detail=f"Ungrounded claim (overlap={best_overlap:.2f}): {sentence[:80]}",
                )
            )

    if flags:
        logger.warning("hallucination_detected", count=len(flags))

    # Hallucination flags are informational — don't block, just flag
    return GuardrailResult(passed=True, flags=flags)
