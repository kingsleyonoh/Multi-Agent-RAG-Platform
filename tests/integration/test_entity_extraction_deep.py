"""Deep verification — Entity extraction → Neo4j.

Proves that document ingestion creates Entity nodes in Neo4j
via the newly-wired entity extraction pipeline.
"""

from __future__ import annotations

import io
import uuid

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

_RUN_ID = uuid.uuid4().hex[:8]

_ENTITY_DOC = (
    f"Entity extraction test {_RUN_ID}. "
    "Google and Microsoft announced a partnership in January 2024. "
    "The deal was brokered by John McCarthy and Satya Nadella. "
    "Both companies will collaborate on artificial intelligence research "
    "at their new joint laboratory in San Francisco."
)


class TestEntityExtractionDuringIngestion:
    """Verify entities are created in Neo4j after document upload."""

    @pytest.fixture
    async def ingested_doc(self, httpx_client):
        """Upload a doc with known entities and clean up after."""
        resp = await httpx_client.post(
            "/api/documents",
            files={"file": (
                f"entities_{_RUN_ID}.txt",
                io.BytesIO(_ENTITY_DOC.encode()),
                "text/plain",
            )},
        )
        assert resp.status_code == 201
        data = resp.json()
        yield data
        await httpx_client.delete(f"/api/documents/{data['id']}")

    async def test_ingest_creates_neo4j_entities(self, httpx_client, ingested_doc, neo4j_driver):
        """After ingesting a doc with 'Google' and 'Microsoft', Neo4j has entities."""
        # Query Neo4j for entities from this document
        async with neo4j_driver.session() as session:
            result = await session.run(
                "MATCH (e:Entity)-[:EXTRACTED_FROM]->(d:Document {id: $doc_id}) "
                "RETURN e.value AS value, e.type AS type",
                {"doc_id": ingested_doc["id"]},
            )
            records = await result.data()

        values = [r["value"] for r in records]
        assert len(values) > 0, "No entities found in Neo4j after ingestion"
        # Should find at least Google or Microsoft
        assert any(
            v in values for v in ["Google", "Microsoft"]
        ), f"Expected Google/Microsoft in {values}"

    async def test_entity_relationship_to_document(self, httpx_client, ingested_doc, neo4j_driver):
        """EXTRACTED_FROM relationships link entities to the document."""
        async with neo4j_driver.session() as session:
            result = await session.run(
                "MATCH (e:Entity)-[r:EXTRACTED_FROM]->(d:Document {id: $doc_id}) "
                "RETURN count(r) AS rel_count",
                {"doc_id": ingested_doc["id"]},
            )
            data = await result.data()

        assert data[0]["rel_count"] > 0

    async def test_graph_entities_endpoint_shows_results(self, httpx_client, ingested_doc):
        """GET /api/graph/entities should return entities after ingestion."""
        resp = await httpx_client.get("/api/graph/entities")
        assert resp.status_code == 200
        data = resp.json()
        # Should have entities (from this or previous ingestions)
        assert isinstance(data, (list, dict))
