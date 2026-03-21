"""Unit tests for document extractors (TDD Red → Green).

Covers text, PDF, Markdown, and URL extractors with happy-path
and edge-case scenarios.
"""

from __future__ import annotations

import pytest


# ── Text extractor ──────────────────────────────────────────────


class TestTextExtractor:
    """Tests for src.ingestion.extractors.text.extract."""

    def test_passthrough_plain_text(self) -> None:
        from src.ingestion.extractors.text import extract

        assert extract("hello world") == "hello world"

    def test_strips_leading_trailing_whitespace(self) -> None:
        from src.ingestion.extractors.text import extract

        assert extract("  hello  ") == "hello"

    def test_empty_string_raises(self) -> None:
        from src.ingestion.extractors.text import extract

        with pytest.raises(ValueError, match="EMPTY_DOCUMENT"):
            extract("")

    def test_whitespace_only_raises(self) -> None:
        from src.ingestion.extractors.text import extract

        with pytest.raises(ValueError, match="EMPTY_DOCUMENT"):
            extract("   \n\t  ")


# ── PDF extractor ───────────────────────────────────────────────


class TestPdfExtractor:
    """Tests for src.ingestion.extractors.pdf.extract."""

    def test_extracts_text_from_pdf_bytes(self, tmp_path) -> None:
        """Create a minimal PDF with pdfplumber-writable text."""
        from src.ingestion.extractors.pdf import extract
        import pdfplumber
        from io import BytesIO

        # Create a tiny PDF using reportlab-free approach:
        # we use fpdf2 if available, else just test with a known fixture
        # For simplicity, create a PDF-like fixture via pdfplumber's test util
        # Instead, let's create a real PDF with the simplest possible method
        import struct

        # Use a pre-built minimal PDF with text "Hello"
        # This is the simplest valid PDF with extractable text
        pdf_content = (
            b"%PDF-1.0\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
            b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
            b"4 0 obj<</Length 44>>stream\n"
            b"BT /F1 12 Tf 100 700 Td (Hello PDF) Tj ET\n"
            b"endstream\nendobj\n"
            b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
            b"xref\n0 6\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"0000000266 00000 n \n"
            b"0000000360 00000 n \n"
            b"trailer<</Size 6/Root 1 0 R>>\n"
            b"startxref\n431\n%%EOF"
        )

        result = extract(pdf_content)
        assert "Hello PDF" in result

    def test_empty_pdf_raises(self, tmp_path) -> None:
        from src.ingestion.extractors.pdf import extract

        # Minimal valid PDF with no text content
        pdf_content = (
            b"%PDF-1.0\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
            b"/Resources<<>>>>endobj\n"
            b"xref\n0 4\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"trailer<</Size 4/Root 1 0 R>>\n"
            b"startxref\n226\n%%EOF"
        )

        with pytest.raises(ValueError, match="(?i)no.*text|empty|scanned"):
            extract(pdf_content)


# ── Markdown extractor ──────────────────────────────────────────


class TestMarkdownExtractor:
    """Tests for src.ingestion.extractors.markdown.extract."""

    def test_passthrough_plain_markdown(self) -> None:
        from src.ingestion.extractors.markdown import extract

        md = "# Title\n\nSome content here."
        result = extract(md)
        assert "# Title" in result
        assert "Some content here." in result

    def test_strips_yaml_frontmatter(self) -> None:
        from src.ingestion.extractors.markdown import extract

        md = "---\ntitle: Test\nauthor: AI\n---\n\n# Body\n\nContent."
        result = extract(md)
        assert "title: Test" not in result
        assert "# Body" in result
        assert "Content." in result

    def test_no_frontmatter_unchanged(self) -> None:
        from src.ingestion.extractors.markdown import extract

        md = "# Just a heading\n\nParagraph text."
        assert extract(md) == md.strip()

    def test_empty_after_strip_raises(self) -> None:
        from src.ingestion.extractors.markdown import extract

        md = "---\ntitle: Only Frontmatter\n---\n"
        with pytest.raises(ValueError, match="EMPTY_DOCUMENT"):
            extract(md)


# ── URL extractor ───────────────────────────────────────────────


class TestUrlExtractor:
    """Tests for src.ingestion.extractors.url.extract (async)."""

    @pytest.mark.asyncio
    async def test_extracts_text_from_html(self, respx_mock) -> None:
        from src.ingestion.extractors.url import extract

        html = "<html><body><h1>Title</h1><p>Hello world</p></body></html>"
        respx_mock.get("https://example.com/page").mock(
            return_value=__import__("httpx").Response(200, text=html),
        )

        result = await extract("https://example.com/page")
        assert "Title" in result
        assert "Hello world" in result

    @pytest.mark.asyncio
    async def test_strips_script_and_style_tags(self, respx_mock) -> None:
        from src.ingestion.extractors.url import extract

        html = (
            "<html><body>"
            "<script>var x = 1;</script>"
            "<style>body{color:red}</style>"
            "<p>Visible text</p>"
            "</body></html>"
        )
        respx_mock.get("https://example.com/js").mock(
            return_value=__import__("httpx").Response(200, text=html),
        )

        result = await extract("https://example.com/js")
        assert "var x" not in result
        assert "color:red" not in result
        assert "Visible text" in result

    @pytest.mark.asyncio
    async def test_non_200_raises(self, respx_mock) -> None:
        from src.ingestion.extractors.url import extract

        respx_mock.get("https://example.com/404").mock(
            return_value=__import__("httpx").Response(404),
        )

        with pytest.raises(ValueError, match="(?i)status|fetch|failed"):
            await extract("https://example.com/404")

    @pytest.mark.asyncio
    async def test_empty_body_raises(self, respx_mock) -> None:
        from src.ingestion.extractors.url import extract

        html = "<html><body></body></html>"
        respx_mock.get("https://example.com/empty").mock(
            return_value=__import__("httpx").Response(200, text=html),
        )

        with pytest.raises(ValueError, match="EMPTY_DOCUMENT"):
            await extract("https://example.com/empty")
