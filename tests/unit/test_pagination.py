"""Unit tests for cursor-based pagination utility (TDD)."""

from __future__ import annotations

import uuid

import pytest

from src.lib.pagination import encode_cursor, decode_cursor, clamp_limit


class TestEncodeDecode:
    """Round-trip encoding / decoding of cursor values."""

    def test_round_trip(self) -> None:
        uid = uuid.uuid4()
        assert decode_cursor(encode_cursor(uid)) == uid

    def test_encode_returns_string(self) -> None:
        result = encode_cursor(uuid.uuid4())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_decode_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            decode_cursor("not-a-valid-cursor")


class TestClampLimit:
    """Tests for limit clamping."""

    def test_default_value(self) -> None:
        assert clamp_limit(None) == 25

    def test_custom_value_within_range(self) -> None:
        assert clamp_limit(50) == 50

    def test_exceeds_max_clamped(self) -> None:
        assert clamp_limit(200) == 100

    def test_zero_becomes_default(self) -> None:
        assert clamp_limit(0) == 25

    def test_negative_becomes_default(self) -> None:
        assert clamp_limit(-5) == 25
