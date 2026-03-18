"""Initial schema — all seven PRD tables.

Revision ID: 001
Revises: None
Create Date: 2026-03-18

Creates: documents, chunks, conversations, messages,
         prompts, evaluations, semantic_cache.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgvector extension is available.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- documents (PRD 4.1) ---
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "content_hash", sa.Text(), nullable=False, unique=True,
        ),
        sa.Column("metadata", sa.JSON(), server_default="{}"),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("status", sa.Text(), server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # --- chunks (PRD 4.2) ---
    op.create_table(
        "chunks",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "document_id",
            sa.UUID(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("metadata", sa.JSON(), server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    # ivfflat index for vector similarity search.
    op.execute(
        "CREATE INDEX ix_chunks_embedding ON chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # --- conversations (PRD 4.3) ---
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("model_preference", sa.Text(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), server_default="0"),
        sa.Column(
            "total_cost_usd", sa.Numeric(10, 6), server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    # --- messages (PRD 4.3) ---
    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.UUID(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_used", sa.Text(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tool_calls", sa.JSON(), nullable=True),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column("guardrail_flags", sa.JSON(), server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at"],
    )

    # --- prompts (PRD 4.4) ---
    op.create_table(
        "prompts",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("model_hint", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("metadata", sa.JSON(), server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_prompts_name_active", "prompts", ["name", "is_active"],
    )

    # --- evaluations (PRD 4.5) ---
    op.create_table(
        "evaluations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "message_id",
            sa.UUID(),
            sa.ForeignKey("messages.id"),
            nullable=False,
        ),
        sa.Column("metric", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(5, 4), nullable=False),
        sa.Column("details", sa.JSON(), server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_evaluations_message_id", "evaluations", ["message_id"])
    op.create_index(
        "ix_evaluations_metric_score", "evaluations", ["metric", "score"],
    )

    # --- semantic_cache (PRD 4.6) ---
    op.create_table(
        "semantic_cache",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("query_embedding", Vector(1536), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("model_used", sa.Text(), nullable=False),
        sa.Column("hit_count", sa.Integer(), server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=False,
        ),
    )
    # ivfflat index for semantic similarity.
    op.execute(
        "CREATE INDEX ix_semantic_cache_query_embedding ON semantic_cache "
        "USING ivfflat (query_embedding vector_cosine_ops) WITH (lists = 50)"
    )
    op.create_index(
        "ix_semantic_cache_expires_at", "semantic_cache", ["expires_at"],
    )


def downgrade() -> None:
    op.drop_table("semantic_cache")
    op.drop_table("evaluations")
    op.drop_table("prompts")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.execute("DROP EXTENSION IF EXISTS vector")
