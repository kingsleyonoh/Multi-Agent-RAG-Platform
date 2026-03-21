"""Batch 18 — Monitoring & Alerting RED phase tests.

Tests for:
  - UptimeChecker: polls /api/health and tracks status history
  - AlertingEngine: evaluates alert rules and fires alerts
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Uptime Checker ───────────────────────────────────────────────────


class TestUptimeChecker:
    """Tests for src/monitoring/uptime.py."""

    def test_import(self):
        """Module must be importable."""
        from src.monitoring.uptime import UptimeChecker

    def test_init_stores_url(self):
        from src.monitoring.uptime import UptimeChecker

        checker = UptimeChecker(url="http://localhost:8000/api/health")
        assert checker.url == "http://localhost:8000/api/health"

    def test_init_empty_history(self):
        from src.monitoring.uptime import UptimeChecker

        checker = UptimeChecker(url="http://localhost:8000/api/health")
        assert checker.history == []

    @pytest.mark.asyncio
    async def test_check_healthy(self):
        """check() should record True for 200 status."""
        from src.monitoring.uptime import UptimeChecker

        checker = UptimeChecker(url="http://localhost:8000/api/health")
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance
            result = await checker.check()
        assert result is True
        assert len(checker.history) == 1

    @pytest.mark.asyncio
    async def test_check_unhealthy(self):
        """check() should record False for non-200 status."""
        from src.monitoring.uptime import UptimeChecker

        checker = UptimeChecker(url="http://localhost:8000/api/health")
        mock_response = MagicMock()
        mock_response.status_code = 500
        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance
            result = await checker.check()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_network_error(self):
        """check() should record False on network error."""
        from src.monitoring.uptime import UptimeChecker

        checker = UptimeChecker(url="http://localhost:8000/api/health")
        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=Exception("Connection refused"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance
            result = await checker.check()
        assert result is False


# ── Alerting Engine ──────────────────────────────────────────────────


class TestAlertingEngine:
    """Tests for src/monitoring/alerting.py."""

    def test_import(self):
        """Module must be importable."""
        from src.monitoring.alerting import AlertingEngine

    def test_init_default_rules(self):
        from src.monitoring.alerting import AlertingEngine

        engine = AlertingEngine()
        assert len(engine.rules) > 0

    def test_health_critical_after_3_failures(self):
        """3 consecutive health failures should trigger critical alert."""
        from src.monitoring.alerting import AlertingEngine

        engine = AlertingEngine()
        context = {"health_checks": [False, False, False]}
        alerts = engine.evaluate(context)
        critical = [a for a in alerts if a["severity"] == "critical"]
        assert len(critical) >= 1

    def test_no_alert_on_healthy(self):
        """All healthy checks should not trigger alert."""
        from src.monitoring.alerting import AlertingEngine

        engine = AlertingEngine()
        context = {
            "health_checks": [True, True, True],
            "daily_llm_spend": 5.0,
            "guardrail_block_rate": 0.1,
            "avg_relevance": 0.8,
        }
        alerts = engine.evaluate(context)
        assert len(alerts) == 0

    def test_llm_spend_warning(self):
        """Daily LLM spend > $10 triggers warning."""
        from src.monitoring.alerting import AlertingEngine

        engine = AlertingEngine()
        context = {"health_checks": [True], "daily_llm_spend": 15.0}
        alerts = engine.evaluate(context)
        warnings = [
            a for a in alerts if a["severity"] == "warning" and "spend" in a["rule"]
        ]
        assert len(warnings) >= 1

    def test_guardrail_block_rate_warning(self):
        """Block rate > 30% triggers warning."""
        from src.monitoring.alerting import AlertingEngine

        engine = AlertingEngine()
        context = {"health_checks": [True], "guardrail_block_rate": 0.35}
        alerts = engine.evaluate(context)
        warnings = [
            a
            for a in alerts
            if a["severity"] == "warning" and "guardrail" in a["rule"]
        ]
        assert len(warnings) >= 1

    def test_low_relevance_warning(self):
        """Avg RAG relevance < 0.6 triggers warning."""
        from src.monitoring.alerting import AlertingEngine

        engine = AlertingEngine()
        context = {"health_checks": [True], "avg_relevance": 0.5}
        alerts = engine.evaluate(context)
        warnings = [
            a
            for a in alerts
            if a["severity"] == "warning" and "relevance" in a["rule"]
        ]
        assert len(warnings) >= 1
