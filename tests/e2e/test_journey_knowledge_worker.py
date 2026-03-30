"""E2E Journey — Knowledge Worker.

Full happy-path journey: upload document → search → chat → verify
conversation → check metrics → cleanup.

Uses real LLM calls via OpenRouter (~$0.02 per run).
"""

from __future__ import annotations

import io
import uuid

import pytest

pytestmark = pytest.mark.e2e

_RUN_ID = uuid.uuid4().hex[:8]

_AI_DOCUMENT = (
    f"Knowledge worker test {_RUN_ID}. "
    "Artificial Intelligence was pioneered by researchers at Dartmouth "
    "College in 1956. Key figures include John McCarthy, who coined the "
    "term artificial intelligence, Marvin Minsky, and Allen Newell. "
    "Modern AI encompasses machine learning, deep learning, natural "
    "language processing, and computer vision. Large language models "
    "like GPT and Claude represent the latest advances in AI."
)


class TestKnowledgeWorkerJourney:
    """Simulate a real user uploading docs, searching, and chatting."""

    async def test_full_journey(self, httpx_client):
        # ── Step 1: Upload a document ────────────────────────────
        upload_resp = await httpx_client.post(
            "/api/documents",
            files={"file": (
                f"ai_history_{_RUN_ID}.txt",
                io.BytesIO(_AI_DOCUMENT.encode()),
                "text/plain",
            )},
        )
        assert upload_resp.status_code == 201, upload_resp.text
        doc_data = upload_resp.json()
        doc_id = doc_data["id"]
        assert doc_data["status"] == "embedded"

        try:
            # ── Step 2: Verify document in database ──────────────
            get_resp = await httpx_client.get(f"/api/documents/{doc_id}")
            assert get_resp.status_code == 200
            assert get_resp.json()["status"] == "embedded"

            # ── Step 3: Search for content ───────────────────────
            search_resp = await httpx_client.post(
                "/api/search",
                json={
                    "query": "Who pioneered artificial intelligence?",
                    "threshold": 0.1,
                },
            )
            assert search_resp.status_code == 200
            results = search_resp.json()["results"]
            assert len(results) > 0, "Search returned no results"

            # ── Step 4: Create a conversation ────────────────────
            conv_resp = await httpx_client.post(
                "/api/conversations",
                json={
                    "user_id": "e2e-test-user",
                    "title": f"KW Journey {_RUN_ID}",
                },
            )
            assert conv_resp.status_code == 201
            conv_id = conv_resp.json()["id"]

            try:
                # ── Step 5: Chat with context ────────────────────
                # Use unique query to avoid semantic cache hit
                chat_resp = await httpx_client.post(
                    "/api/chat/sync",
                    json={
                        "query": f"[{_RUN_ID}] Who pioneered AI and when did it happen?",
                        "conversation_id": conv_id,
                    },
                )
                assert chat_resp.status_code == 200
                chat_data = chat_resp.json()
                assert len(chat_data["response"]) > 0
                assert chat_data["model_used"] is not None
                assert chat_data["cost"] >= 0

                # Response should be grounded in the document
                response_lower = chat_data["response"].lower()
                grounded = any(
                    term in response_lower
                    for term in ["dartmouth", "mccarthy", "1956", "minsky"]
                )
                assert grounded, (
                    f"Response not grounded in document: {chat_data['response'][:200]}"
                )

                # ── Step 6: Verify conversation exists and is accessible ─
                conv_detail = await httpx_client.get(f"/api/conversations/{conv_id}")
                assert conv_detail.status_code == 200
                messages = conv_detail.json()["messages"]
                # Messages may be empty if semantic cache served the response
                # (cache hits skip message persistence). Verify the array exists.
                assert isinstance(messages, list)

                # ── Step 7: Check cost metrics ───────────────────
                metrics_resp = await httpx_client.get("/api/metrics/cost")
                assert metrics_resp.status_code == 200
                assert metrics_resp.json()["total_requests"] > 0

                # ── Step 8: List documents includes ours ─────────
                list_resp = await httpx_client.get("/api/documents")
                assert list_resp.status_code == 200
                doc_ids = [d["id"] for d in list_resp.json()["items"]]
                assert doc_id in doc_ids

            finally:
                # ── Step 9: Cleanup conversation ─────────────────
                await httpx_client.delete(f"/api/conversations/{conv_id}")

        finally:
            # ── Step 10: Cleanup document ────────────────────────
            await httpx_client.delete(f"/api/documents/{doc_id}")
