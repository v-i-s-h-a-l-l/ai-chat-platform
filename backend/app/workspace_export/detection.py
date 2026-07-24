"""Export format detection and user intent parsing."""

from __future__ import annotations

import re

from app.workspace_export.markdown_parser import parse_markdown
from app.workspace_export.models import ExportFormat, TableBlock

_EXPORT_INTENT_PATTERNS: list[tuple[re.Pattern[str], ExportFormat]] = [
    (re.compile(r"\b(?:download|save|export).{0,20}\b(?:as|to)\s+pdf\b", re.I), ExportFormat.PDF),
    (re.compile(r"\b(?:download|save|export).{0,20}\b(?:as|to)\s+(?:word|docx?)\b", re.I), ExportFormat.DOCX),
    (re.compile(r"\b(?:download|save|export).{0,20}\b(?:as|to)\s+(?:excel|xlsx?)\b", re.I), ExportFormat.XLSX),
    (re.compile(r"\b(?:download|save|export).{0,20}\b(?:as|to)\s+(?:markdown|md)\b", re.I), ExportFormat.MARKDOWN),
    (re.compile(r"\b(?:download|save|export).{0,20}\b(?:as|to)\s+(?:text|txt)\b", re.I), ExportFormat.TEXT),
]

_TABULAR_KEYWORDS = re.compile(
    r"\b("
    r"schedule|timeline|table|comparison|compare|task|tasks|tracker|tracking|"
    r"sprint|roadmap|checklist|matrix|rating|score|budget|forecast|"
    r"\d+\s*(?:days?|weeks?|months?|hours?)"
    r")\b",
    re.IGNORECASE,
)


def detect_export_intent(message: str) -> ExportFormat | None:
    text = message.strip()
    if not text:
        return None
    for pattern, fmt in _EXPORT_INTENT_PATTERNS:
        if pattern.search(text):
            return fmt
    return None


def supports_excel(content: str) -> bool:
    doc = parse_markdown(content)
    tables = [block for block in doc.blocks if isinstance(block, TableBlock)]
    if not tables:
        return False
    if len(tables) >= 1:
        return True
    if _TABULAR_KEYWORDS.search(content):
        return True
    return bool(tables)


def available_formats(content: str) -> list[ExportFormat]:
    formats = [
        ExportFormat.PDF,
        ExportFormat.DOCX,
        ExportFormat.MARKDOWN,
        ExportFormat.TEXT,
    ]
    if supports_excel(content):
        formats.insert(2, ExportFormat.XLSX)
    return formats
