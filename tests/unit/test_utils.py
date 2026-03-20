"""Unit tests for src/lib/utils.py — shared utility functions.

Tests written TDD-first (Red Phase) before implementation exists.
Covers: SHA-256 content hashing, UTC timestamp generation, text truncation.
"""

from __future__ import annotations

from datetime import datetime, timezone


class TestContentHash:
    """SHA-256 content hashing for document dedup (PRD §4.1)."""

    def test_returns_hex_string(self) -> None:
        from src.lib.utils import content_hash

        result = content_hash("hello world")
        # SHA-256 hex digest is exactly 64 characters
        assert isinstance(result, str)
        assert len(result) == 64

    def test_deterministic_same_input(self) -> None:
        from src.lib.utils import content_hash

        assert content_hash("same content") == content_hash("same content")

    def test_different_content_different_hash(self) -> None:
        from src.lib.utils import content_hash

        assert content_hash("document A") != content_hash("document B")

    def test_matches_known_sha256(self) -> None:
        """Verify against a known SHA-256 digest."""
        from src.lib.utils import content_hash

        # SHA-256 of empty string is well-known
        expected = (
            "e3b0c44298fc1c149afbf4c8996fb924"
            "27ae41e4649b934ca495991b7852b855"
        )
        assert content_hash("") == expected

    def test_handles_unicode(self) -> None:
        from src.lib.utils import content_hash

        result = content_hash("日本語テスト 🚀")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_whitespace_sensitivity(self) -> None:
        """Leading/trailing whitespace produces different hash."""
        from src.lib.utils import content_hash

        assert content_hash("hello") != content_hash(" hello ")

    def test_normalises_line_endings(self) -> None:
        r"""CRLF and LF produce the same hash for cross-platform dedup."""
        from src.lib.utils import content_hash

        assert content_hash("line1\r\nline2") == content_hash("line1\nline2")


class TestUtcNow:
    """UTC timestamp helper (CODING_STANDARDS_DOMAIN §Python/FastAPI)."""

    def test_returns_datetime(self) -> None:
        from src.lib.utils import utc_now

        result = utc_now()
        assert isinstance(result, datetime)

    def test_has_utc_timezone(self) -> None:
        from src.lib.utils import utc_now

        result = utc_now()
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_is_close_to_now(self) -> None:
        from src.lib.utils import utc_now

        before = datetime.now(timezone.utc)
        result = utc_now()
        after = datetime.now(timezone.utc)
        assert before <= result <= after


class TestTruncateText:
    """Text truncation for log messages and error summaries."""

    def test_short_text_unchanged(self) -> None:
        from src.lib.utils import truncate_text

        assert truncate_text("short", max_len=100) == "short"

    def test_long_text_truncated_with_ellipsis(self) -> None:
        from src.lib.utils import truncate_text

        result = truncate_text("a" * 200, max_len=50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_exact_length_unchanged(self) -> None:
        from src.lib.utils import truncate_text

        text = "x" * 50
        assert truncate_text(text, max_len=50) == text

    def test_empty_string(self) -> None:
        from src.lib.utils import truncate_text

        assert truncate_text("", max_len=10) == ""

    def test_default_max_len(self) -> None:
        """Default max_len should be 200."""
        from src.lib.utils import truncate_text

        long_text = "a" * 300
        result = truncate_text(long_text)
        assert len(result) == 200
        assert result.endswith("...")
