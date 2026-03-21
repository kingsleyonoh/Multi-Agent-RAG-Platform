"""Unit tests for ingestion pipeline (TDD).

All database and embedding calls are fully mocked.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestIngestDocument:
    """Tests for src.ingestion.pipeline.ingest_document."""

    @pytest.mark.asyncio
    async def test_empty_content_raises(self) -> None:
        from src.ingestion.pipeline import ingest_document

        with pytest.raises(ValueError, match="EMPTY_DOCUMENT"):
            await ingest_document(
                title="Test",
                source="upload",
                content="",
                metadata={},
                session=AsyncMock(),
                settings=MagicMock(),
            )

    @pytest.mark.asyncio
    async def test_duplicate_returns_existing_id(self) -> None:
        from src.ingestion.pipeline import ingest_document

        existing_id = uuid.uuid4()
        mock_session = AsyncMock()
        # Simulate finding an existing document by content_hash
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(id=existing_id)
        mock_session.execute.return_value = mock_result

        settings = MagicMock(
            CHUNK_SIZE=512, CHUNK_OVERLAP=50,
            OPENROUTER_BASE_URL="https://openrouter.ai/api/v1",
            OPENROUTER_API_KEY="key", EMBEDDING_MODEL="model",
        )

        result = await ingest_document(
            title="Test",
            source="upload",
            content="Some content",
            metadata={},
            session=mock_session,
            settings=settings,
        )
        assert result == existing_id

    @pytest.mark.asyncio
    @patch("src.ingestion.pipeline.embed_texts", new_callable=AsyncMock)
    async def test_successful_ingestion_returns_uuid(self, mock_embed) -> None:
        from src.ingestion.pipeline import ingest_document

        mock_embed.return_value = [[0.1] * 1536]

        mock_session = AsyncMock()
        # No duplicate found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        settings = MagicMock(
            CHUNK_SIZE=512, CHUNK_OVERLAP=50,
            OPENROUTER_BASE_URL="https://openrouter.ai/api/v1",
            OPENROUTER_API_KEY="key", EMBEDDING_MODEL="model",
        )

        result = await ingest_document(
            title="My Doc",
            source="upload",
            content="Hello world content here.",
            metadata={},
            session=mock_session,
            settings=settings,
        )
        assert isinstance(result, uuid.UUID)

    @pytest.mark.asyncio
    @patch("src.ingestion.pipeline.embed_texts", new_callable=AsyncMock)
    async def test_embed_failure_raises(self, mock_embed) -> None:
        from src.ingestion.pipeline import ingest_document

        mock_embed.side_effect = RuntimeError("API failed")

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        settings = MagicMock(
            CHUNK_SIZE=512, CHUNK_OVERLAP=50,
            OPENROUTER_BASE_URL="https://openrouter.ai/api/v1",
            OPENROUTER_API_KEY="key", EMBEDDING_MODEL="model",
        )

        with pytest.raises(RuntimeError, match="API failed"):
            await ingest_document(
                title="Test",
                source="upload",
                content="Some content",
                metadata={},
                session=mock_session,
                settings=settings,
            )
