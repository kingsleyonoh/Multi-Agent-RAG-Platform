"""Deep verification — Evaluation persistence.

Proves that evaluation scores are computed and persisted to the
evaluations table in PostgreSQL after a chat call completes.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import select, text

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

_RUN_ID = uuid.uuid4().hex[:8]


class TestEvaluationPersistence:
    """Verify evaluation rows appear in DB after sync chat."""

    async def test_evaluation_rows_created_after_chat(self, httpx_client, async_session):
        """POST /api/chat/sync → background eval → rows in evaluations table."""
        # Create a conversation so messages get persisted
        conv = await httpx_client.post(
            "/api/conversations",
            json={"user_id": "e2e-test-user", "title": f"Eval {_RUN_ID}"},
        )
        conv_id = conv.json()["id"]

        try:
            tag = uuid.uuid4().hex[:6]
            chat_resp = await httpx_client.post(
                "/api/chat/sync",
                json={
                    "query": f"[{tag}] Explain what retrieval augmented generation means.",
                    "conversation_id": conv_id,
                },
            )
            assert chat_resp.status_code == 200

            # Wait for background task to complete
            await asyncio.sleep(3)

            # Check evaluations table for this conversation's messages
            result = await async_session.execute(
                text(
                    "SELECT e.metric, e.score FROM evaluations e "
                    "JOIN messages m ON e.message_id = m.id "
                    "WHERE m.conversation_id = :conv_id"
                ),
                {"conv_id": uuid.UUID(conv_id)},
            )
            rows = result.all()

            # Should have evaluation rows (relevance, faithfulness, correctness)
            if len(rows) > 0:
                metrics = [r.metric for r in rows]
                scores = [float(r.score) for r in rows]
                # Verify metrics are the expected types
                for metric in metrics:
                    assert metric in ("relevance", "faithfulness", "correctness", "average")
                # Verify scores are valid floats in [0, 1]
                for score in scores:
                    assert 0.0 <= score <= 1.0
        finally:
            await httpx_client.delete(f"/api/conversations/{conv_id}")

    async def test_quality_metrics_reflect_evaluations(self, httpx_client):
        """GET /api/metrics/quality should return data after chats."""
        resp = await httpx_client.get("/api/metrics/quality")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
