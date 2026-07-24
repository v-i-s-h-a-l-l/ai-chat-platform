"""Pre-render validation for export documents."""

from __future__ import annotations

import re

from app.workspace_export.models import (
    HeadingBlock,
    HorizontalRuleBlock,
    ParsedDocument,
)

_REPLACEMENT_CHAR = "\ufffd"
_RAW_HTML_RE = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)


class ExportValidationError(ValueError):
    pass


def validate_export_document(markdown: str, doc: ParsedDocument, html: str) -> None:
    """Raise ExportValidationError if the document is not safe to render."""
    errors: list[str] = []

    if _REPLACEMENT_CHAR in markdown or _REPLACEMENT_CHAR in html:
        errors.append("Unicode replacement characters detected")

    if _RAW_HTML_RE.search(markdown):
        errors.append("Raw HTML (<br>) detected in source markdown")

    if re.search(r"<\s*br\s*/?\s*>", html, re.IGNORECASE):
        errors.append("Raw <br> tags in layout HTML")

    if re.search(r"<\s*(?:br|div|span|p)\b", markdown, re.IGNORECASE):
        errors.append("Unresolved HTML in repaired markdown")

    if not _heading_hierarchy_valid(doc):
        errors.append("Invalid heading hierarchy")

    if _has_malformed_tables(doc):
        errors.append("Malformed table structure")

    if errors:
        raise ExportValidationError("; ".join(errors))


def _heading_hierarchy_valid(doc: ParsedDocument) -> bool:
    last_level = 0
    for block in doc.blocks:
        if isinstance(block, HeadingBlock):
            if block.level > last_level + 1 and last_level != 0:
                return False
            last_level = block.level
    return True


def _has_malformed_tables(doc: ParsedDocument) -> bool:
    from app.workspace_export.models import TableBlock

    for block in doc.blocks:
        if isinstance(block, TableBlock):
            if not block.headers:
                return True
            col_count = len(block.headers)
            for row in block.rows:
                if len(row) != col_count:
                    return True
    return False


def filter_horizontal_rules(doc: ParsedDocument) -> ParsedDocument:
    """Keep horizontal rules only between major sections (H1/H2)."""
    filtered = []
    previous: object | None = None
    for block in doc.blocks:
        if isinstance(block, HorizontalRuleBlock):
            if isinstance(previous, HeadingBlock) and previous.level <= 2:
                filtered.append(block)
            previous = block
            continue
        filtered.append(block)
        previous = block
    return ParsedDocument(blocks=filtered, title=doc.title)
