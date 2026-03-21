"""Unit tests for SQLAlchemy ORM models.

Tests validate schema correctness by inspecting SQLAlchemy metadata —
no database connection required.
"""

import uuid
from decimal import Decimal

import pytest

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


# ---------------------------------------------------------------------------
# Table registration
# ---------------------------------------------------------------------------


class TestTableRegistration:
    """All 7 models must be registered in Base.metadata."""

    EXPECTED_TABLES = {
        "documents",
        "chunks",
        "conversations",
        "messages",
        "prompts",
        "evaluations",
        "semantic_cache",
    }

    def test_all_tables_registered(self):
        """Base.metadata.tables contains all 7 PRD table names."""
        registered = set(Base.metadata.tables.keys())
        assert self.EXPECTED_TABLES.issubset(registered)

    def test_no_extra_tables(self):
        """Only the 7 expected tables exist — no accidental extras."""
        registered = set(Base.metadata.tables.keys())
        assert registered == self.EXPECTED_TABLES


# ---------------------------------------------------------------------------
# Model __tablename__
# ---------------------------------------------------------------------------


class TestTableNames:
    """Each model maps to the correct table name."""

    @pytest.mark.parametrize(
        "model, expected_name",
        [
            (Document, "documents"),
            (Chunk, "chunks"),
            (Conversation, "conversations"),
            (Message, "messages"),
            (Prompt, "prompts"),
            (Evaluation, "evaluations"),
            (SemanticCache, "semantic_cache"),
        ],
    )
    def test_tablename(self, model, expected_name):
        assert model.__tablename__ == expected_name


# ---------------------------------------------------------------------------
# Column presence
# ---------------------------------------------------------------------------


def _col_names(model) -> set[str]:
    """Return the set of column names for a model."""
    return {c.name for c in model.__table__.columns}


class TestDocumentColumns:
    """Document model has all PRD 4.1 columns."""

    EXPECTED = {
        "id", "title", "source", "content", "content_hash",
        "metadata", "chunk_count", "status", "created_at", "updated_at",
    }

    def test_columns(self):
        assert _col_names(Document) == self.EXPECTED


class TestChunkColumns:
    """Chunk model has all PRD 4.2 columns including embedding."""

    EXPECTED = {
        "id", "document_id", "chunk_index", "content",
        "token_count", "embedding", "metadata", "created_at",
    }

    def test_columns(self):
        assert _col_names(Chunk) == self.EXPECTED

    def test_document_fk(self):
        """chunk.document_id references documents.id."""
        col = Chunk.__table__.c.document_id
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "documents.id" in fk_targets


class TestConversationColumns:
    """Conversation model has all PRD 4.3 columns."""

    EXPECTED = {
        "id", "user_id", "title", "model_preference",
        "total_tokens", "total_cost_usd", "created_at", "updated_at",
    }

    def test_columns(self):
        assert _col_names(Conversation) == self.EXPECTED


class TestMessageColumns:
    """Message model has all PRD 4.3 columns."""

    EXPECTED = {
        "id", "conversation_id", "role", "content", "model_used",
        "tokens_in", "tokens_out", "cost_usd", "latency_ms",
        "tool_calls", "sources", "guardrail_flags", "created_at",
    }

    def test_columns(self):
        assert _col_names(Message) == self.EXPECTED

    def test_conversation_fk(self):
        """message.conversation_id references conversations.id."""
        col = Message.__table__.c.conversation_id
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "conversations.id" in fk_targets


class TestPromptColumns:
    """Prompt model has all PRD 4.4 columns."""

    EXPECTED = {
        "id", "name", "version", "template", "model_hint",
        "is_active", "metadata", "created_at", "updated_at",
    }

    def test_columns(self):
        assert _col_names(Prompt) == self.EXPECTED


class TestEvaluationColumns:
    """Evaluation model has all PRD 4.5 columns."""

    EXPECTED = {
        "id", "message_id", "metric", "score",
        "details", "created_at",
    }

    def test_columns(self):
        assert _col_names(Evaluation) == self.EXPECTED

    def test_message_fk(self):
        """evaluation.message_id references messages.id."""
        col = Evaluation.__table__.c.message_id
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "messages.id" in fk_targets


class TestSemanticCacheColumns:
    """SemanticCache model has all PRD 4.6 columns."""

    EXPECTED = {
        "id", "query_embedding", "query_text", "response",
        "model_used", "hit_count", "created_at", "expires_at",
    }

    def test_columns(self):
        assert _col_names(SemanticCache) == self.EXPECTED


# ---------------------------------------------------------------------------
# Inheritance check
# ---------------------------------------------------------------------------


class TestInheritance:
    """All models inherit from the shared Base."""

    @pytest.mark.parametrize(
        "model",
        [Document, Chunk, Conversation, Message, Prompt, Evaluation, SemanticCache],
    )
    def test_inherits_base(self, model):
        assert issubclass(model, Base)
