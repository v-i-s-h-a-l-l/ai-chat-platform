"""Intelligent export filename generation."""

from __future__ import annotations

import re
from datetime import datetime

from app.workspace_export.markdown_parser import parse_markdown
from app.workspace_export.models import ExportFormat

_SUFFIXES = {
    ExportFormat.PDF: "pdf",
    ExportFormat.DOCX: "docx",
    ExportFormat.XLSX: "xlsx",
    ExportFormat.MARKDOWN: "md",
    ExportFormat.TEXT: "txt",
}


def build_filename(
    content: str,
    export_format: ExportFormat,
    project_name: str | None = None,
) -> str:
    doc = parse_markdown(content)
    base = doc.title or _infer_title(content) or project_name or "AI_Response"
    base = _sanitize(base)
    suffix = _SUFFIXES[export_format]
    return f"{base}.{suffix}"


def _infer_title(content: str) -> str | None:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if len(stripped) > 8:
            return stripped[:60]
    return None


def _sanitize(value: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned[:80] or "AI_Response"
