"""Unit tests for src/db/neo4j – Neo4j driver wrapper (mocked)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# — these imports must resolve once src/db/neo4j.py exists —
from src.db.neo4j import get_driver, verify_connectivity, close_driver


# ── Fixtures ────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_driver_cache():
    """Reset module-level driver cache between tests."""
    from src.db import neo4j as mod
    mod._drivers.clear()
    yield
    mod._drivers.clear()


# ── get_driver ──────────────────────────────────────────────────

class TestGetDriver:
    """Verify cached async driver creation."""

    @patch("src.db.neo4j.AsyncGraphDatabase")
    def test_returns_async_driver(self, mock_agd: MagicMock) -> None:
        mock_driver = MagicMock()
        mock_agd.driver.return_value = mock_driver

        result = get_driver("bolt://localhost:7687", "neo4j", "pass")

        mock_agd.driver.assert_called_once_with(
            "bolt://localhost:7687", auth=("neo4j", "pass")
        )
        assert result is mock_driver

    @patch("src.db.neo4j.AsyncGraphDatabase")
    def test_caches_by_uri(self, mock_agd: MagicMock) -> None:
        mock_driver = MagicMock()
        mock_agd.driver.return_value = mock_driver

        d1 = get_driver("bolt://localhost:7687", "neo4j", "pass")
        d2 = get_driver("bolt://localhost:7687", "neo4j", "pass")

        assert d1 is d2
        assert mock_agd.driver.call_count == 1

    @patch("src.db.neo4j.AsyncGraphDatabase")
    def test_different_uri_different_drivers(self, mock_agd: MagicMock) -> None:
        mock_agd.driver.side_effect = [MagicMock(), MagicMock()]

        d1 = get_driver("bolt://host-a:7687", "neo4j", "pass")
        d2 = get_driver("bolt://host-b:7687", "neo4j", "pass")

        assert d1 is not d2
        assert mock_agd.driver.call_count == 2


# ── verify_connectivity ────────────────────────────────────────

class TestVerifyConnectivity:
    """Graceful degradation: returns False on failure."""

    @pytest.mark.asyncio
    async def test_returns_false_on_error(self) -> None:
        driver = AsyncMock()
        driver.verify_connectivity.side_effect = Exception("refused")

        ok = await verify_connectivity(driver)

        assert ok is False
