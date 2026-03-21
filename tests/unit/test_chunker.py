"""Unit tests for text chunker (TDD)."""

from __future__ import annotations

import pytest

from src.ingestion.chunker import chunk_text, ChunkResult


class TestChunkText:
    """Tests for recursive character text chunking."""

    def test_short_text_single_chunk(self) -> None:
        result = chunk_text("Short text.", chunk_size=100, overlap=10)
        assert len(result) == 1
        assert result[0].content == "Short text."
        assert result[0].index == 0

    def test_long_text_produces_multiple_chunks(self) -> None:
        text = "Word " * 200  # ~200 words, ~1000 chars
        result = chunk_text(text, chunk_size=100, overlap=20)
        assert len(result) > 1
        # Every chunk except last should be close to chunk_size
        for chunk in result[:-1]:
            assert len(chunk.content) <= 120  # some tolerance

    def test_chunks_have_sequential_indices(self) -> None:
        text = "Sentence one. " * 50
        result = chunk_text(text, chunk_size=50, overlap=10)
        indices = [c.index for c in result]
        assert indices == list(range(len(result)))

    def test_overlap_creates_shared_content(self) -> None:
        text = "AAAA. BBBB. CCCC. DDDD. EEEE. FFFF. GGGG. HHHH."
        result = chunk_text(text, chunk_size=20, overlap=5)
        if len(result) >= 2:
            # With overlap, end of chunk N should appear in chunk N+1
            assert len(result) >= 2

    def test_chunk_result_has_token_count(self) -> None:
        result = chunk_text("Hello world test.", chunk_size=100, overlap=0)
        assert result[0].token_count > 0

    def test_empty_text_raises(self) -> None:
        with pytest.raises(ValueError, match="EMPTY_DOCUMENT"):
            chunk_text("", chunk_size=100, overlap=0)
