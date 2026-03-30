"""L1 — Deep PostgreSQL integration tests.

Tests real CRUD operations on all 7 ORM tables, pgvector cosine
similarity, cascade deletes, and uniqueness constraints against a
live PostgreSQL instance (Docker).

All tests use the ``async_session`` fixture which auto-rolls back.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from src.db.models import (
    Base,
    Chunk,
    Conversation,
    Document,
    Evaluation,
    Message,
    Prompt,
    SemanticCache,
)

pytestmark = pytest.mark.integration


# ── Helpers ──────────────────────────────────────────────────────


def _zero_vector(dim: int = 1536) -> list[float]:
    """Return a zero embedding of the given dimension."""
    return [0.0] * dim


def _unit_vector(index: int, dim: int = 1536) -> list[float]:
    """Return a unit vector with 1.0 at *index* and 0.0 elsewhere."""
    vec = [0.0] * dim
    vec[index % dim] = 1.0
    return vec


def _make_document(**overrides) -> Document:
    """Create a Document instance with sensible defaults."""
    defaults = {
        "title": f"Test Doc {uuid.uuid4().hex[:8]}",
        "source": "test",
        "content": "Sample content for testing.",
        "content_hash": uuid.uuid4().hex,
    }
    defaults.update(overrides)
    return Document(**defaults)


# ── Document Table ───────────────────────────────────────────────


class TestDocumentCRUD:
    """Create / read / verify defaults on the documents table."""

    async def test_create_and_read_document(self, async_session):
        doc = _make_document()
        async_session.add(doc)
        await async_session.flush()

        result = await async_session.execute(
            select(Document).where(Document.id == doc.id)
        )
        loaded = result.scalar_one()

        assert loaded.title == doc.title
        assert loaded.source == "test"
        assert loaded.content == "Sample content for testing."
        assert loaded.created_at is not None

    async def test_document_content_hash_uniqueness(self, async_session):
        hash_val = uuid.uuid4().hex
        doc1 = _make_document(content_hash=hash_val)
        doc2 = _make_document(content_hash=hash_val)

        async_session.add(doc1)
        await async_session.flush()

        # Use a savepoint so the IntegrityError doesn't break the session
        nested = await async_session.begin_nested()
        async_session.add(doc2)
        with pytest.raises(IntegrityError):
            await async_session.flush()
        await nested.rollback()


# ── Chunk Table + pgvector ────────────────────────────────────────


class TestChunkWithPgvector:
    """Chunk CRUD and pgvector embedding operations."""

    async def test_create_chunk_with_embedding(self, async_session):
        doc = _make_document()
        async_session.add(doc)
        await async_session.flush()

        chunk = Chunk(
            document_id=doc.id,
            chunk_index=0,
            content="Test chunk content.",
            token_count=5,
            embedding=_zero_vector(),
        )
        async_session.add(chunk)
        await async_session.flush()

        # Verify the vector dimension via raw SQL
        row = await async_session.execute(
            text("SELECT vector_dims(embedding) FROM chunks WHERE id = :id"),
            {"id": chunk.id},
        )
        dims = row.scalar_one()
        assert dims == 1536

    async def test_pgvector_cosine_similarity_ranking(self, async_session):
        """Insert two chunks with known embeddings, verify cosine ranking."""
        doc = _make_document()
        async_session.add(doc)
        await async_session.flush()

        # Chunk A: unit vector at index 0
        chunk_a = Chunk(
            document_id=doc.id, chunk_index=0,
            content="Similar chunk", token_count=2,
            embedding=_unit_vector(0),
        )
        # Chunk B: unit vector at index 1 (orthogonal to query)
        chunk_b = Chunk(
            document_id=doc.id, chunk_index=1,
            content="Different chunk", token_count=2,
            embedding=_unit_vector(1),
        )
        async_session.add_all([chunk_a, chunk_b])
        await async_session.flush()

        # Query vector matches chunk A — use cast() to avoid :: syntax
        # which conflicts with SQLAlchemy's :param binding.
        from pgvector.sqlalchemy import Vector as VectorType
        from sqlalchemy import cast, column, literal

        query_vec = _unit_vector(0)
        query_str = "[" + ",".join(str(v) for v in query_vec) + "]"

        rows = await async_session.execute(
            text(
                "SELECT id, 1 - (embedding <=> cast(:qvec AS vector)) AS score "
                "FROM chunks WHERE document_id = :doc_id "
                "ORDER BY score DESC"
            ),
            {"qvec": query_str, "doc_id": doc.id},
        )
        results = rows.all()
        assert len(results) == 2
        assert results[0].id == chunk_a.id  # most similar
        assert results[0].score > results[1].score


# ── Cascade Deletes ──────────────────────────────────────────────


class TestCascadeDeletes:
    """Foreign key CASCADE behavior."""

    async def test_document_cascade_deletes_chunks(self, async_session):
        doc = _make_document()
        async_session.add(doc)
        await async_session.flush()

        for i in range(3):
            async_session.add(
                Chunk(
                    document_id=doc.id, chunk_index=i,
                    content=f"chunk {i}", token_count=2,
                    embedding=_zero_vector(),
                )
            )
        await async_session.flush()

        await async_session.delete(doc)
        await async_session.flush()

        remaining = await async_session.execute(
            select(Chunk).where(Chunk.document_id == doc.id)
        )
        assert remaining.scalars().all() == []

    async def test_conversation_cascade_deletes_messages(self, async_session):
        conv = Conversation(user_id="cascade-test", title="Cascade Test")
        async_session.add(conv)
        await async_session.flush()

        for role in ("user", "assistant", "user"):
            async_session.add(
                Message(conversation_id=conv.id, role=role, content="Hello")
            )
        await async_session.flush()

        await async_session.delete(conv)
        await async_session.flush()

        remaining = await async_session.execute(
            select(Message).where(Message.conversation_id == conv.id)
        )
        assert remaining.scalars().all() == []


# ── Conversation + Message ───────────────────────────────────────


class TestConversationMessageCRUD:
    """Conversation and message round-trip."""

    async def test_conversation_and_messages(self, async_session):
        conv = Conversation(user_id="test-user", title="Test Conv")
        async_session.add(conv)
        await async_session.flush()

        msg = Message(
            conversation_id=conv.id,
            role="user",
            content="Hello world",
            model_used="openai/gpt-4o-mini",
            tokens_in=10,
            tokens_out=20,
        )
        async_session.add(msg)
        await async_session.flush()

        loaded = await async_session.execute(
            select(Message).where(Message.conversation_id == conv.id)
        )
        messages = loaded.scalars().all()
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].tokens_in == 10


# ── Prompt ───────────────────────────────────────────────────────


class TestPromptCRUD:
    """Prompt versioning and uniqueness."""

    async def test_prompt_version_increment(self, async_session):
        prompt = Prompt(
            name=f"test_prompt_{uuid.uuid4().hex[:8]}",
            template="Hello {{ name }}",
        )
        async_session.add(prompt)
        await async_session.flush()

        # Default version = 1 (server_default)
        await async_session.refresh(prompt)
        assert prompt.version == 1

        # Simulate update by incrementing version
        prompt.version = 2
        prompt.template = "Updated: {{ name }}"
        await async_session.flush()
        await async_session.refresh(prompt)
        assert prompt.version == 2


# ── Evaluation ───────────────────────────────────────────────────


class TestEvaluationFK:
    """Evaluation → Message foreign key."""

    async def test_evaluation_linked_to_message(self, async_session):
        conv = Conversation(user_id="eval-test")
        async_session.add(conv)
        await async_session.flush()

        msg = Message(
            conversation_id=conv.id, role="assistant", content="Answer."
        )
        async_session.add(msg)
        await async_session.flush()

        evaluation = Evaluation(
            message_id=msg.id,
            metric="relevance",
            score=0.85,
            details={"source": "auto"},
        )
        async_session.add(evaluation)
        await async_session.flush()

        loaded = await async_session.execute(
            select(Evaluation).where(Evaluation.message_id == msg.id)
        )
        evals = loaded.scalars().all()
        assert len(evals) == 1
        assert float(evals[0].score) == pytest.approx(0.85, abs=0.001)


# ── SemanticCache ────────────────────────────────────────────────


class TestSemanticCacheTable:
    """SemanticCache table round-trip with vector embedding."""

    async def test_semantic_cache_round_trip(self, async_session):
        now = datetime.now(timezone.utc)
        cache_entry = SemanticCache(
            query_embedding=_zero_vector(),
            query_text="What is RAG?",
            response="RAG is Retrieval-Augmented Generation.",
            model_used="openai/gpt-4o-mini",
            expires_at=now + timedelta(hours=24),
        )
        async_session.add(cache_entry)
        await async_session.flush()

        loaded = await async_session.execute(
            select(SemanticCache).where(SemanticCache.id == cache_entry.id)
        )
        entry = loaded.scalar_one()
        assert entry.query_text == "What is RAG?"
        assert entry.response == "RAG is Retrieval-Augmented Generation."
        assert entry.model_used == "openai/gpt-4o-mini"


# ── pgvector Extension ───────────────────────────────────────────


class TestPgvectorExtension:
    """Verify pgvector extension is installed."""

    async def test_pgvector_extension_exists(self, async_session):
        result = await async_session.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        ext = result.scalar_one_or_none()
        assert ext == "vector"
