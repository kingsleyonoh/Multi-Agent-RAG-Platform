"""Batch 16 — Background Jobs RED phase tests.

Tests for:
  - cache_cleanup: remove expired entries from SemanticCache
  - conversation_summary: summarize long conversations
  - evaluation_aggregation: compute aggregate quality metrics
  - cost_budget_reset: reset daily spend budgets
  - graph_sync: entity extraction → graph upsert from documents
"""

import time
from unittest.mock import MagicMock, patch

import pytest


# ── Cache Cleanup ────────────────────────────────────────────────────


class TestCacheCleanup:
    """Tests for src.jobs.cache_cleanup."""

    def test_removes_expired_entries(self):
        """Entries older than TTL should be removed."""
        from src.jobs.cache_cleanup import cleanup_expired_entries
        from src.cache.semantic import SemanticCache

        cache = SemanticCache(ttl_hours=1)
        # Add an entry and backdate it
        cache.entries.append({
            "query": "old query",
            "response": "old response",
            "embedding": [1.0, 0.0],
            "created_at": time.time() - 7200,  # 2h ago
            "hit_count": 0,
        })
        cache.entries.append({
            "query": "fresh query",
            "response": "fresh response",
            "embedding": [0.0, 1.0],
            "created_at": time.time(),
            "hit_count": 0,
        })

        removed = cleanup_expired_entries(cache)
        assert removed == 1
        assert len(cache.entries) == 1
        assert cache.entries[0]["query"] == "fresh query"

    def test_no_expired_returns_zero(self):
        """When nothing is expired, return 0 removals."""
        from src.jobs.cache_cleanup import cleanup_expired_entries
        from src.cache.semantic import SemanticCache

        cache = SemanticCache(ttl_hours=24)
        cache.entries.append({
            "query": "q",
            "response": "r",
            "embedding": [1.0],
            "created_at": time.time(),
            "hit_count": 0,
        })
        removed = cleanup_expired_entries(cache)
        assert removed == 0
        assert len(cache.entries) == 1

    def test_empty_cache_returns_zero(self):
        """Empty cache should return 0."""
        from src.jobs.cache_cleanup import cleanup_expired_entries
        from src.cache.semantic import SemanticCache

        cache = SemanticCache()
        removed = cleanup_expired_entries(cache)
        assert removed == 0


# ── Conversation Summary ─────────────────────────────────────────────


class TestConversationSummary:
    """Tests for src.jobs.conversation_summary."""

    def test_summarizes_long_conversations(self):
        """Conversations exceeding threshold should be summarized."""
        from src.jobs.conversation_summary import summarize_long_conversations

        conversations = {
            "sess-1": ["msg"] * 30,  # exceeds threshold of 20
            "sess-2": ["msg"] * 5,   # under threshold
        }
        results = summarize_long_conversations(conversations, threshold=20)
        assert len(results) == 1
        assert "sess-1" in results

    def test_no_long_conversations_returns_empty(self):
        """All short conversations → empty result."""
        from src.jobs.conversation_summary import summarize_long_conversations

        conversations = {"s1": ["msg"] * 5}
        results = summarize_long_conversations(conversations, threshold=20)
        assert results == {}

    def test_empty_conversations_returns_empty(self):
        """No conversations → empty result."""
        from src.jobs.conversation_summary import summarize_long_conversations

        results = summarize_long_conversations({}, threshold=20)
        assert results == {}


# ── Evaluation Aggregation ───────────────────────────────────────────


class TestEvaluationAggregation:
    """Tests for src.jobs.evaluation_aggregation."""

    def test_aggregate_returns_averages(self):
        """Should compute average relevance, faithfulness, correctness."""
        from src.jobs.evaluation_aggregation import aggregate_metrics

        history = [
            {"relevance": 0.8, "faithfulness": 0.9, "correctness": 0.7},
            {"relevance": 0.6, "faithfulness": 0.7, "correctness": 0.5},
        ]
        agg = aggregate_metrics(history)
        assert agg["avg_relevance"] == pytest.approx(0.7, abs=0.01)
        assert agg["avg_faithfulness"] == pytest.approx(0.8, abs=0.01)
        assert agg["avg_correctness"] == pytest.approx(0.6, abs=0.01)
        assert agg["total_evaluations"] == 2

    def test_aggregate_empty_history(self):
        """Empty history should return zeros."""
        from src.jobs.evaluation_aggregation import aggregate_metrics

        agg = aggregate_metrics([])
        assert agg["avg_relevance"] == 0.0
        assert agg["total_evaluations"] == 0

    def test_aggregate_includes_flagged_count(self):
        """Should count flagged entries."""
        from src.jobs.evaluation_aggregation import aggregate_metrics

        history = [
            {"relevance": 0.8, "faithfulness": 0.9, "correctness": 0.7, "flagged": False},
            {"relevance": 0.3, "faithfulness": 0.2, "correctness": 0.1, "flagged": True},
        ]
        agg = aggregate_metrics(history)
        assert agg["flagged_count"] == 1


# ── Cost Budget Reset ────────────────────────────────────────────────


class TestCostBudgetReset:
    """Tests for src.jobs.cost_budget_reset."""

    def test_resets_all_users(self):
        """All user budgets should be reset to zero spend."""
        from src.jobs.cost_budget_reset import reset_daily_budgets

        tracker = {
            "user-1": {"daily_spend": 5.00, "budget": 10.00},
            "user-2": {"daily_spend": 8.50, "budget": 10.00},
        }
        count = reset_daily_budgets(tracker)
        assert count == 2
        assert tracker["user-1"]["daily_spend"] == 0.0
        assert tracker["user-2"]["daily_spend"] == 0.0

    def test_preserves_budget_limit(self):
        """Budget cap should not change during reset."""
        from src.jobs.cost_budget_reset import reset_daily_budgets

        tracker = {"u1": {"daily_spend": 3.0, "budget": 15.0}}
        reset_daily_budgets(tracker)
        assert tracker["u1"]["budget"] == 15.0

    def test_empty_tracker_returns_zero(self):
        """No users → 0 resets."""
        from src.jobs.cost_budget_reset import reset_daily_budgets

        assert reset_daily_budgets({}) == 0


# ── Knowledge Graph Sync ─────────────────────────────────────────────


class TestGraphSync:
    """Tests for src.jobs.graph_sync."""

    def test_extracts_and_upserts(self):
        """Should extract entities then upsert into graph store."""
        from src.jobs.graph_sync import sync_graph

        extractor = MagicMock()
        extractor.extract.return_value = [
            {"entity": "Python", "type": "TECHNOLOGY"},
        ]
        graph_store = MagicMock()

        count = sync_graph(
            content="Python is great",
            entity_extractor=extractor,
            graph_store=graph_store,
        )
        extractor.extract.assert_called_once_with("Python is great")
        graph_store.upsert_entities.assert_called_once()
        assert count == 1

    def test_no_entities_returns_zero(self):
        """Empty extraction → 0 upserts."""
        from src.jobs.graph_sync import sync_graph

        extractor = MagicMock()
        extractor.extract.return_value = []
        graph_store = MagicMock()

        count = sync_graph(
            content="nothing here",
            entity_extractor=extractor,
            graph_store=graph_store,
        )
        assert count == 0
        graph_store.upsert_entities.assert_not_called()

    def test_returns_entity_count(self):
        """Should return the number of entities upserted."""
        from src.jobs.graph_sync import sync_graph

        extractor = MagicMock()
        extractor.extract.return_value = [
            {"entity": "A", "type": "X"},
            {"entity": "B", "type": "Y"},
            {"entity": "C", "type": "Z"},
        ]
        graph_store = MagicMock()

        count = sync_graph(
            content="A B C",
            entity_extractor=extractor,
            graph_store=graph_store,
        )
        assert count == 3
