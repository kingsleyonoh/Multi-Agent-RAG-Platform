"""L3 — Document API integration tests.

Tests the full document lifecycle (upload, list, get, delete)
against the live running server with real PostgreSQL + embeddings.
"""

from __future__ import annotations

import io
import uuid

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

# Unique content per test run to avoid dedup collisions.
_RUN_ID = uuid.uuid4().hex[:8]

_TEST_CONTENT = (
    f"Test document {_RUN_ID}. "
    "Retrieval-Augmented Generation (RAG) combines retrieval systems "
    "with language models. RAG uses vector embeddings to find relevant "
    "documents and passes them as context to generate grounded answers."
)


class TestDocumentUpload:
    """Upload documents via the API."""

    async def test_upload_text_document(self, httpx_client):
        file_data = _TEST_CONTENT.encode()
        resp = await httpx_client.post(
            "/api/documents",
            files={"file": (f"test_{_RUN_ID}.txt", io.BytesIO(file_data), "text/plain")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["status"] == "embedded"

        # Cleanup
        await httpx_client.delete(f"/api/documents/{data['id']}")

    async def test_upload_no_file_returns_422(self, httpx_client):
        resp = await httpx_client.post("/api/documents")
        assert resp.status_code == 422


class TestDocumentLifecycle:
    """Full lifecycle: upload → get → list → delete → verify gone."""

    @pytest.fixture
    async def uploaded_doc(self, httpx_client):
        """Upload a document and return its data; delete after test."""
        content = f"Lifecycle test {uuid.uuid4().hex[:8]}. Python is a language."
        resp = await httpx_client.post(
            "/api/documents",
            files={"file": ("lifecycle.txt", io.BytesIO(content.encode()), "text/plain")},
        )
        data = resp.json()
        yield data
        # Cleanup (ignore 404 if already deleted by the test)
        await httpx_client.delete(f"/api/documents/{data['id']}")

    async def test_get_uploaded_document(self, httpx_client, uploaded_doc):
        doc_id = uploaded_doc["id"]
        resp = await httpx_client.get(f"/api/documents/{doc_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == doc_id
        assert data["status"] == "embedded"

    async def test_list_documents_includes_uploaded(self, httpx_client, uploaded_doc):
        resp = await httpx_client.get("/api/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        doc_ids = [item["id"] for item in data["items"]]
        assert uploaded_doc["id"] in doc_ids

    async def test_delete_document(self, httpx_client, uploaded_doc):
        doc_id = uploaded_doc["id"]
        resp = await httpx_client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 204

    async def test_get_deleted_document_404(self, httpx_client):
        # Upload then delete, then verify 404
        content = f"Delete test {uuid.uuid4().hex[:8]}."
        upload = await httpx_client.post(
            "/api/documents",
            files={"file": ("del.txt", io.BytesIO(content.encode()), "text/plain")},
        )
        doc_id = upload.json()["id"]
        await httpx_client.delete(f"/api/documents/{doc_id}")

        resp = await httpx_client.get(f"/api/documents/{doc_id}")
        assert resp.status_code == 404

    async def test_duplicate_content_returns_existing_id(self, httpx_client):
        content = f"Dedup test {uuid.uuid4().hex[:8]}. Unique content here."
        file1 = await httpx_client.post(
            "/api/documents",
            files={"file": ("dup1.txt", io.BytesIO(content.encode()), "text/plain")},
        )
        id1 = file1.json()["id"]

        file2 = await httpx_client.post(
            "/api/documents",
            files={"file": ("dup2.txt", io.BytesIO(content.encode()), "text/plain")},
        )
        id2 = file2.json()["id"]

        assert id1 == id2

        # Cleanup
        await httpx_client.delete(f"/api/documents/{id1}")
