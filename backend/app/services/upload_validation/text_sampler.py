"""Lightweight in-memory text sampling for upload validation (first page only)."""

from __future__ import annotations

import re
from io import BytesIO

from app.services.upload_validation.types import DocumentSample

_MAX_SAMPLE_CHARS = 2500
_HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


def sample_document(filename: str, mime_type: str, data: bytes) -> DocumentSample:
    """Extract title, first-page text, and page count without persisting the file."""
    if mime_type == "application/pdf":
        first_page, page_count = _sample_pdf(data)
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        first_page = _sample_docx(data)
        page_count = None
    else:
        first_page = _sample_text(data)
        page_count = 1

    title = _infer_title(filename, first_page)
    return DocumentSample(
        title=title,
        first_page_text=first_page[:_MAX_SAMPLE_CHARS],
        page_count=page_count,
        filename=filename,
    )


def _sample_text(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore").strip()


def _sample_pdf(data: bytes) -> tuple[str, int | None]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        page_count = len(reader.pages)
        if page_count == 0:
            return "", 0
        first = reader.pages[0].extract_text() or ""
        return first.strip(), page_count
    except Exception:
        return data.decode("utf-8", errors="ignore")[:_MAX_SAMPLE_CHARS].strip(), None


def _sample_docx(data: bytes) -> str:
    try:
        from docx import Document as DocxDocument

        doc = DocxDocument(BytesIO(data))
        parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n".join(parts)[:_MAX_SAMPLE_CHARS].strip()
    except Exception:
        return ""


def _infer_title(filename: str, text: str) -> str:
    for match in _HEADING_PATTERN.finditer(text):
        heading = match.group(1).strip()
        if heading:
            return heading[:200]
    stem = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
    return stem[:200] if stem else filename
