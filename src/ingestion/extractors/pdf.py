"""PDF extractor.

Extracts text from PDF bytes using pdfplumber.  Raises if the
document appears to be scanned / contains no extractable text.

Usage::

    from src.ingestion.extractors.pdf import extract

    text = extract(pdf_bytes)
"""

from __future__ import annotations

import io

import pdfplumber


def extract(file_bytes: bytes) -> str:
    """Extract text from *file_bytes* (a PDF binary).

    Concatenates text from every page separated by newlines.

    Raises:
        ValueError: If no text could be extracted (likely scanned image).
    """
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    full_text = "\n".join(text_parts).strip()
    if not full_text:
        raise ValueError(
            "No extractable text found — document may be scanned/image-only"
        )
    return full_text
