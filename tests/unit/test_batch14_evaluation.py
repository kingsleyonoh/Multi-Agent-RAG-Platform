"""Batch 14 — Evaluation Harness RED phase tests.

Tests for:
  - Relevance scorer
  - Faithfulness scorer
  - Correctness scorer
  - Evaluation harness (orchestrates all three)
  - Metrics API endpoints (cost + quality)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ── Scorers ──────────────────────────────────────────────────────────

from src.evaluation.relevance import RelevanceScorer
from src.evaluation.faithfulness import FaithfulnessScorer
from src.evaluation.correctness import CorrectnessScorer


class TestRelevanceScorer:
    """Relevance: are the retrieved chunks relevant to the query?"""

    def test_score_returns_float(self):
        scorer = RelevanceScorer()
        score = scorer.score(
            query="What is Python?",
            chunks=["Python is a programming language."],
        )
        assert isinstance(score, float)

    def test_score_in_range(self):
        scorer = RelevanceScorer()
        score = scorer.score(query="q", chunks=["c"])
        assert 0.0 <= score <= 1.0

    def test_high_relevance(self):
        scorer = RelevanceScorer()
        score = scorer.score(
            query="What is Python?",
            chunks=["Python is a high-level programming language."],
        )
        assert score >= 0.3  # keyword-overlap heuristic seam


class TestFaithfulnessScorer:
    """Faithfulness: is the response grounded in the source chunks?"""

    def test_score_returns_float(self):
        scorer = FaithfulnessScorer()
        score = scorer.score(
            response="Python is great.",
            chunks=["Python is a great language."],
        )
        assert isinstance(score, float)

    def test_score_in_range(self):
        scorer = FaithfulnessScorer()
        score = scorer.score(response="r", chunks=["c"])
        assert 0.0 <= score <= 1.0

    def test_high_faithfulness(self):
        scorer = FaithfulnessScorer()
        score = scorer.score(
            response="Python is a programming language.",
            chunks=["Python is a programming language used worldwide."],
        )
        assert score >= 0.5  # keyword-overlap heuristic seam


class TestCorrectnessScorer:
    """Correctness: does the response actually answer the question?"""

    def test_score_returns_float(self):
        scorer = CorrectnessScorer()
        score = scorer.score(
            query="What is Python?",
            response="Python is a programming language.",
        )
        assert isinstance(score, float)

    def test_score_in_range(self):
        scorer = CorrectnessScorer()
        score = scorer.score(query="q", response="r")
        assert 0.0 <= score <= 1.0


# ── Evaluation Harness ───────────────────────────────────────────────

from src.evaluation.harness import EvaluationHarness


class TestEvaluationHarness:
    """Harness runs all three scorers and returns aggregated results."""

    def test_evaluate_returns_dict(self):
        harness = EvaluationHarness()
        result = harness.evaluate(
            query="What is Python?",
            response="Python is a programming language.",
            chunks=["Python is a high-level language."],
        )
        assert isinstance(result, dict)

    def test_evaluate_contains_all_scores(self):
        harness = EvaluationHarness()
        result = harness.evaluate(
            query="q", response="r", chunks=["c"],
        )
        assert "relevance" in result
        assert "faithfulness" in result
        assert "correctness" in result

    def test_evaluate_flags_low_quality(self):
        """Responses below threshold should be flagged."""
        harness = EvaluationHarness(min_threshold=0.99)
        result = harness.evaluate(
            query="q", response="r", chunks=["c"],
        )
        # With seam defaults, scores should be below 0.99
        assert result.get("flagged") is True

    def test_evaluate_passes_high_quality(self):
        harness = EvaluationHarness(min_threshold=0.0)
        result = harness.evaluate(
            query="q", response="r", chunks=["c"],
        )
        assert result.get("flagged") is False

    def test_evaluate_stores_history(self):
        harness = EvaluationHarness()
        harness.evaluate(query="q", response="r", chunks=["c"])
        assert len(harness.history) == 1


# ── Metrics API ──────────────────────────────────────────────────────

from src.api.routes.metrics import router as metrics_router


class TestMetricsAPIEndpoints:
    """GET /api/metrics/cost and /api/metrics/quality."""

    @pytest.fixture()
    def client(self):
        app = FastAPI()
        app.include_router(metrics_router, prefix="/api/metrics")
        return TestClient(app)

    def test_cost_endpoint(self, client):
        resp = client.get("/api/metrics/cost")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cost" in data

    def test_quality_endpoint(self, client):
        resp = client.get("/api/metrics/quality")
        assert resp.status_code == 200
        data = resp.json()
        assert "avg_relevance" in data
        assert "avg_faithfulness" in data
