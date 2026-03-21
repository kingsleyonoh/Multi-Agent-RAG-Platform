"""Uptime checker — polls a health endpoint and records status history.

Usage:
    checker = UptimeChecker(url="http://localhost:8000/api/health")
    is_up = await checker.check()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class UptimeChecker:
    """Polls a health endpoint and maintains history of check results."""

    url: str
    history: list[dict[str, Any]] = field(default_factory=list)
    timeout: float = 5.0

    async def check(self) -> bool:
        """Perform a single health check.

        Returns:
            True if endpoint returns 200, False otherwise.
        """
        timestamp = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.url, timeout=self.timeout)
                is_healthy = response.status_code == 200
        except Exception:
            is_healthy = False

        self.history.append(
            {
                "timestamp": timestamp,
                "healthy": is_healthy,
            }
        )
        return is_healthy
