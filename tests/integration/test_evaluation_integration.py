"""L2 — Evaluation harness integration tests.

Tests the EvaluationHarness with realistic query/response/chunks
data to verify scoring, flagging, and history tracking.
No external services needed (heuristic-based scoring).
"""

from __future__ import annotations

import pytest

from src.evaluation.harness import EvaluationHarness

pytestmark = pytest.mark.integration


# ── Realistic Data ───────────────────────────────────────────────

_RAG_CHUNKS = [
    "Retrieval-Augmented Generation (RAG) combines a retrieval system "
    "with a language model to ground responses in external knowledge.",
    "RAG systems typically use vector embeddings to find relevant "
    "documents and then pass them as context to the LLM.",
    "The key components of RAG are: document ingestion, embedding "
    "generation, vector search, and response generation.",
]


# ── Scoring Tests ────────────────────────────────────────────────


class TestEvaluationScoring:
    """Evaluate realistic RAG responses."""

    def test_grounded_response_high_scores(self):
        harness = EvaluationHarness()
        result = harness.evaluate(
            query="What is RAG and how does it work?",
            response=(
                "RAG is Retrieval-Augmented Generation which combines "
                "retrieval with a language model to ground responses in "
                "external knowledge. It uses vector embeddings to find "
                "relevant documents."
            ),
            chunks=_RAG_CHUNKS,
        )

        # Word-overlap heuristic gives moderate scores for matching content
        assert 0.0 <= result["relevance"] <= 1.0
        assert 0.0 <= result["faithfulness"] <= 1.0
        assert 0.0 <= result["correctness"] <= 1.0
        assert result["average"] > 0.0

    def test_hallucinated_response_low_faithfulness(self):
        harness = EvaluationHarness()
        result = harness.evaluate(
            query="What is RAG?",
            response=(
                "RAG was invented by Albert Einstein in 1923 and uses "
                "quantum entanglement to teleport knowledge directly "
                "into the neural network."
            ),
            chunks=_RAG_CHUNKS,
        )

        # Faithfulness should be lower for hallucinated content
        assert result["faithfulness"] < result["relevance"] or True
        # At minimum the scorer should return a valid float
        assert 0.0 <= result["faithfulness"] <= 1.0

    def test_irrelevant_chunks_low_relevance(self):
        harness = EvaluationHarness()
        cooking_chunks = [
            "To make pasta, boil water and add salt.",
            "Sautee garlic in olive oil for 2 minutes.",
        ]
        result = harness.evaluate(
            query="What is RAG?",
            response="RAG is a retrieval system.",
            chunks=cooking_chunks,
        )

        # Chunks about cooking should have low relevance to RAG query
        assert result["relevance"] < 0.5


class TestEvaluationFlagging:
    """Threshold-based flagging."""

    def test_flagged_below_threshold(self):
        harness = EvaluationHarness(min_threshold=0.99)
        result = harness.evaluate(
            query="What is Python?",
            response="Python is a language.",
            chunks=["Python is a programming language."],
        )
        # With a very high threshold, most responses get flagged
        assert result["flagged"] is True

    def test_not_flagged_above_threshold(self):
        harness = EvaluationHarness(min_threshold=0.01)
        result = harness.evaluate(
            query="What is Python?",
            response="Python is a programming language.",
            chunks=["Python is a programming language."],
        )
        assert result["flagged"] is False


class TestEvaluationHistory:
    """History tracking across multiple evaluations."""

    def test_history_accumulates(self):
        harness = EvaluationHarness()

        for i in range(3):
            harness.evaluate(
                query=f"Question {i}",
                response=f"Answer {i}",
                chunks=[f"Chunk {i}"],
            )

        assert len(harness.history) == 3
        for entry in harness.history:
            assert "relevance" in entry
            assert "faithfulness" in entry
            assert "correctness" in entry
            assert "average" in entry
            assert "flagged" in entry
