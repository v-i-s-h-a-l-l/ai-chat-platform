"""Normalize parsed documents so real-world LLM markdown exports reliably."""

from __future__ import annotations

from app.workspace_export.models import (
    DocumentBlock,
    HeadingBlock,
    InlineSpan,
    ParsedDocument,
    TableBlock,
)


def normalize_document(doc: ParsedDocument) -> ParsedDocument:
    """Repair common structural issues before validation and rendering."""
    blocks = [_normalize_block(block) for block in doc.blocks]
    blocks = _normalize_heading_hierarchy(blocks)
    return ParsedDocument(blocks=blocks, title=doc.title)


def _normalize_block(block: DocumentBlock) -> DocumentBlock:
    if isinstance(block, TableBlock):
        return _normalize_table(block)
    return block


def _normalize_table(block: TableBlock) -> TableBlock:
    if not block.headers and not block.rows:
        return block

    if not block.headers and block.rows:
        col_count = max(len(row) for row in block.rows)
        headers = [[InlineSpan(text=f"Column {index + 1}")] for index in range(col_count)]
        rows = block.rows
    else:
        col_count = len(block.headers)
        headers = block.headers
        rows = [_normalize_table_row(row, col_count) for row in block.rows]

    return TableBlock(headers=headers, rows=rows, title=block.title)


def _normalize_table_row(row: list[list[InlineSpan]], col_count: int) -> list[list[InlineSpan]]:
    if len(row) == col_count:
        return row
    if len(row) < col_count:
        return row + [[InlineSpan(text="")] for _ in range(col_count - len(row))]
    return row[:col_count]


def _normalize_heading_hierarchy(blocks: list[DocumentBlock]) -> list[DocumentBlock]:
    last_level = 0
    normalized: list[DocumentBlock] = []
    for block in blocks:
        if isinstance(block, HeadingBlock):
            level = block.level
            if last_level != 0 and level > last_level + 1:
                level = last_level + 1
            last_level = level
            normalized.append(HeadingBlock(level=level, spans=block.spans))
            continue
        normalized.append(block)
    return normalized
