"""Alerting engine — evaluates monitoring rules and fires alerts.

Usage:
    engine = AlertingEngine()
    alerts = engine.evaluate(context)
    # alerts = [{"rule": "health_down", "severity": "critical", "message": "..."}]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AlertRule:
    """A single alerting rule."""

    name: str
    severity: str  # "critical" or "warning"
    check: Callable[[dict[str, Any]], bool]
    message: str


def _health_down(ctx: dict[str, Any]) -> bool:
    """3 consecutive health failures → critical."""
    checks = ctx.get("health_checks", [])
    if len(checks) < 3:
        return False
    return all(not c for c in checks[-3:])


def _llm_spend_high(ctx: dict[str, Any]) -> bool:
    """Daily LLM spend > $10 → warning."""
    return ctx.get("daily_llm_spend", 0.0) > 10.0


def _guardrail_block_rate_high(ctx: dict[str, Any]) -> bool:
    """Guardrail block rate > 30% → warning."""
    return ctx.get("guardrail_block_rate", 0.0) > 0.30


def _low_relevance(ctx: dict[str, Any]) -> bool:
    """Avg RAG relevance < 0.6 → warning."""
    relevance = ctx.get("avg_relevance")
    if relevance is None:
        return False
    return relevance < 0.6


DEFAULT_RULES: list[AlertRule] = [
    AlertRule(
        name="health_down",
        severity="critical",
        check=_health_down,
        message="Health endpoint non-200 for 3 consecutive checks",
    ),
    AlertRule(
        name="llm_spend_high",
        severity="warning",
        check=_llm_spend_high,
        message="Daily LLM spend exceeds $10",
    ),
    AlertRule(
        name="guardrail_block_rate",
        severity="warning",
        check=_guardrail_block_rate_high,
        message="Guardrail block rate exceeds 30%",
    ),
    AlertRule(
        name="low_relevance",
        severity="warning",
        check=_low_relevance,
        message="Average RAG relevance below 0.6",
    ),
]


@dataclass
class AlertingEngine:
    """Evaluates alerting rules against monitoring context."""

    rules: list[AlertRule] = field(default_factory=lambda: list(DEFAULT_RULES))

    def evaluate(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Evaluate all rules and return triggered alerts.

        Args:
            context: Dict with keys like health_checks, daily_llm_spend, etc.

        Returns:
            List of alert dicts with rule, severity, message keys.
        """
        triggered: list[dict[str, Any]] = []
        for rule in self.rules:
            if rule.check(context):
                triggered.append(
                    {
                        "rule": rule.name,
                        "severity": rule.severity,
                        "message": rule.message,
                    }
                )
        return triggered
