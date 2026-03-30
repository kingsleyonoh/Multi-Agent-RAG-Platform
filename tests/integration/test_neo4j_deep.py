"""L1 — Deep Neo4j integration tests.

Tests Entity CRUD, relationship creation, uniqueness constraints,
and Cypher queries against a live Neo4j instance (Docker).

Each test class cleans up its test nodes via a teardown fixture
using a unique label prefix.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration

# Unique prefix so tests don't collide across runs.
_PREFIX = f"test_{uuid.uuid4().hex[:8]}"


# ── Helpers ──────────────────────────────────────────────────────


async def _run_cypher(driver, query: str, **params) -> list[dict]:
    """Execute a Cypher statement and return list of record dicts."""
    async with driver.session() as session:
        result = await session.run(query, params)
        return [dict(record) for record in await result.data()]


async def _cleanup_test_nodes(driver):
    """Delete all nodes whose name starts with the test prefix."""
    await _run_cypher(
        driver,
        "MATCH (n) WHERE n.name STARTS WITH $prefix DETACH DELETE n",
        prefix=_PREFIX,
    )


# ── Entity CRUD ──────────────────────────────────────────────────


class TestEntityCRUD:
    """Create and read Entity nodes."""

    @pytest.fixture(autouse=True)
    async def _cleanup(self, neo4j_driver):
        yield
        await _cleanup_test_nodes(neo4j_driver)

    async def test_create_entity_node(self, neo4j_driver):
        name = f"{_PREFIX}_company"
        await _run_cypher(
            neo4j_driver,
            "MERGE (e:Entity {name: $name, type: 'organization'})",
            name=name,
        )

        rows = await _run_cypher(
            neo4j_driver,
            "MATCH (e:Entity {name: $name}) RETURN e.name AS name, e.type AS type",
            name=name,
        )
        assert len(rows) == 1
        assert rows[0]["name"] == name
        assert rows[0]["type"] == "organization"

    async def test_create_multiple_entity_types(self, neo4j_driver):
        entities = [
            (f"{_PREFIX}_person", "person"),
            (f"{_PREFIX}_org", "organization"),
            (f"{_PREFIX}_date", "date"),
        ]
        for name, etype in entities:
            await _run_cypher(
                neo4j_driver,
                "MERGE (e:Entity {name: $name, type: $type})",
                name=name, type=etype,
            )

        rows = await _run_cypher(
            neo4j_driver,
            "MATCH (e:Entity) WHERE e.name STARTS WITH $prefix "
            "RETURN e.name AS name ORDER BY e.name",
            prefix=_PREFIX,
        )
        assert len(rows) == 3


# ── Constraints ──────────────────────────────────────────────────


class TestConstraints:
    """Verify Entity uniqueness constraint exists."""

    async def test_entity_id_uniqueness_constraint(self, neo4j_driver):
        rows = await _run_cypher(
            neo4j_driver,
            "SHOW CONSTRAINTS YIELD name, labelsOrTypes "
            "WHERE 'Entity' IN labelsOrTypes RETURN name",
        )
        constraint_names = [r["name"] for r in rows]
        assert any("entity" in n.lower() for n in constraint_names), (
            f"Expected entity constraint, found: {constraint_names}"
        )


# ── Relationships ────────────────────────────────────────────────


class TestRelationships:
    """Entity → Entity and Entity → Document relationships."""

    @pytest.fixture(autouse=True)
    async def _cleanup(self, neo4j_driver):
        yield
        await _cleanup_test_nodes(neo4j_driver)

    async def test_create_entity_relationship(self, neo4j_driver):
        name_a = f"{_PREFIX}_alice"
        name_b = f"{_PREFIX}_bob"

        await _run_cypher(
            neo4j_driver,
            "MERGE (a:Entity {name: $a, type: 'person'}) "
            "MERGE (b:Entity {name: $b, type: 'person'}) "
            "MERGE (a)-[:RELATED_TO {relationship: 'colleagues'}]->(b)",
            a=name_a, b=name_b,
        )

        rows = await _run_cypher(
            neo4j_driver,
            "MATCH (a:Entity {name: $a})-[r:RELATED_TO]->(b:Entity {name: $b}) "
            "RETURN r.relationship AS rel",
            a=name_a, b=name_b,
        )
        assert len(rows) == 1
        assert rows[0]["rel"] == "colleagues"

    async def test_query_related_entities(self, neo4j_driver):
        """Create A → Doc ← B, query entities related via Doc."""
        doc_name = f"{_PREFIX}_doc"
        entity_a = f"{_PREFIX}_entity_a"
        entity_b = f"{_PREFIX}_entity_b"

        await _run_cypher(
            neo4j_driver,
            "MERGE (d:Document {name: $doc}) "
            "MERGE (a:Entity {name: $ea, type: 'concept'}) "
            "MERGE (b:Entity {name: $eb, type: 'concept'}) "
            "MERGE (a)-[:EXTRACTED_FROM]->(d) "
            "MERGE (b)-[:EXTRACTED_FROM]->(d)",
            doc=doc_name, ea=entity_a, eb=entity_b,
        )

        rows = await _run_cypher(
            neo4j_driver,
            "MATCH (e:Entity)-[:EXTRACTED_FROM]->(d:Document {name: $doc}) "
            "RETURN e.name AS name ORDER BY e.name",
            doc=doc_name,
        )
        names = [r["name"] for r in rows]
        assert entity_a in names
        assert entity_b in names

    async def test_empty_query_returns_empty(self, neo4j_driver):
        rows = await _run_cypher(
            neo4j_driver,
            "MATCH (e:Entity {name: $name}) RETURN e.name AS name",
            name="nonexistent_entity_that_does_not_exist",
        )
        assert rows == []
