"""Post-generation response formatter for chat-optimized GitHub Flavored Markdown.

Runs after the LLM completes and before persisting/serving assistant messages.
Converts oversized or list-heavy tables into headings + lists, normalizes
spacing, and validates remaining table structure.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CODE_FENCE_PLACEHOLDER = "\u0000CODE_FENCE_"
MAX_CELL_LINES = 3
MAX_CELL_CHARS = 150

LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|(?:\d+\.))\s", re.MULTILINE)
HEADING_RE = re.compile(r"^#{1,6}\s+")
SEPARATOR_ROW_RE = re.compile(
    r"^\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?$"
)


@dataclass
class FormatStats:
    tables_converted: int = 0
    tables_repaired: int = 0


def format_assistant_response(content: str) -> str:
    """Transform LLM markdown into chat-optimized GFM."""
    if not content or not content.strip():
        return content

    protected, blocks = _protect_code_fences(content)
    formatted, stats = _format_protected(protected)
    formatted = _restore_code_fences(formatted, blocks)

    if stats.tables_converted or stats.tables_repaired:
        logger.debug(
            "Response formatter: converted=%d repaired=%d",
            stats.tables_converted,
            stats.tables_repaired,
        )

    return formatted.strip()


def _protect_code_fences(content: str) -> tuple[str, list[str]]:
    blocks: list[str] = []

    def replacer(match: re.Match[str]) -> str:
        idx = len(blocks)
        blocks.append(match.group(0))
        return f"{CODE_FENCE_PLACEHOLDER}{idx}\u0000"

    text = re.sub(r"```[\s\S]*?```", replacer, content)
    return text, blocks


def _restore_code_fences(content: str, blocks: list[str]) -> str:
    def replacer(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        return blocks[idx] if 0 <= idx < len(blocks) else ""

    return re.sub(rf"{CODE_FENCE_PLACEHOLDER}(\d+)\u0000", replacer, content)


def _format_protected(content: str) -> tuple[str, FormatStats]:
    stats = FormatStats()
    lines = content.split("\n")
    output: list[str] = []
    i = 0

    while i < len(lines):
        block_end = _find_table_block_end(lines, i)
        if block_end is None:
            output.append(lines[i])
            i += 1
            continue

        block_lines = lines[i:block_end]
        converted = _process_table_block(block_lines, stats)
        if converted is not None:
            if output and output[-1].strip():
                output.append("")
            output.extend(converted.split("\n"))
            if block_end < len(lines) and lines[block_end].strip():
                output.append("")
        else:
            output.extend(block_lines)

        i = block_end

    normalized = _normalize_markdown("\n".join(output))
    return normalized, stats


def _looks_like_table_row(line: str) -> bool:
    trimmed = line.strip()
    if not trimmed or trimmed.startswith("```"):
        return False
    return "|" in trimmed


def _is_separator_row(line: str) -> bool:
    trimmed = line.strip().replace("||", "|")
    if "-" not in trimmed:
        return False
    return bool(SEPARATOR_ROW_RE.match(trimmed))


def _find_table_block_end(lines: list[str], start: int) -> int | None:
    if not _looks_like_table_row(lines[start]):
        return None

    end = start + 1
    while end < len(lines):
        line = lines[end]
        if not line.strip():
            break
        if _looks_like_table_row(line) or _is_separator_row(line):
            end += 1
            continue
        # Allow continuation lines that belong to a broken table cell.
        if end > start + 1:
            end += 1
            continue
        break

    if end - start < 2:
        return None
    return end


def _split_cells(line: str) -> list[str]:
    trimmed = line.strip().replace("||", "|")
    if trimmed.startswith("|"):
        trimmed = trimmed[1:]
    if trimmed.endswith("|"):
        trimmed = trimmed[:-1]

    cells: list[str] = []
    current: list[str] = []
    i = 0
    while i < len(trimmed):
        ch = trimmed[i]
        if ch == "\\" and i + 1 < len(trimmed):
            current.append(trimmed[i : i + 2])
            i += 2
            continue
        if ch == "|":
            cells.append("".join(current).strip())
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    cells.append("".join(current).strip())
    return cells


def _parse_table_block(block_lines: list[str]) -> tuple[list[str], list[list[str]]] | None:
    non_empty = [line for line in block_lines if line.strip()]
    if len(non_empty) < 2:
        return None

    header = _split_cells(non_empty[0])
    if not header or all(not cell for cell in header):
        return None

    data_start = 1
    if len(non_empty) > 1 and _is_separator_row(non_empty[1]):
        data_start = 2

    rows: list[list[str]] = []
    for line in non_empty[data_start:]:
        if _is_separator_row(line):
            continue

        stripped = line.strip()
        if stripped.startswith("|"):
            rows.append(_split_cells(line))
            continue

        # Continuation line — LLMs often break numbered/bullet lists out of the cell.
        if rows:
            continuation = stripped.rstrip("|").strip()
            rows[-1][-1] = f"{rows[-1][-1]}\n{continuation}".strip()
            continue

        rows.append(_split_cells(line))

    rows = [row for row in rows if any(cell.strip() for cell in row)]
    if not rows:
        return None

    return header, rows


def _cell_violates(cell: str) -> bool:
    stripped = cell.strip()
    if not stripped:
        return False
    if len(stripped) > MAX_CELL_CHARS:
        return True
    if "\n\n" in stripped:
        return True

    lines = stripped.split("\n")
    non_empty = [line for line in lines if line.strip()]
    if len(non_empty) > MAX_CELL_LINES:
        return True
    if LIST_ITEM_RE.search(stripped):
        return True
    return False


def _table_needs_conversion(header: list[str], rows: list[list[str]]) -> bool:
    for cell in header:
        if _cell_violates(cell):
            return True
    for row in rows:
        for cell in row:
            if _cell_violates(cell):
                return True

    # Multi-column explanatory tables (e.g. Stage | Expectations | Preparation)
    # are poor fit for chat; convert when cells are descriptive rather than compact.
    if len(header) >= 3:
        for row in rows:
            for cell in row:
                if len(cell.strip()) > 80:
                    return True

    return False


def _format_cell_content(cell: str) -> str:
    stripped = cell.strip()
    if not stripped:
        return ""

    lines = stripped.split("\n")
    formatted_lines: list[str] = []
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        if LIST_ITEM_RE.match(trimmed):
            formatted_lines.append(trimmed)
        elif re.match(r"^\d+\.\s", trimmed):
            formatted_lines.append(trimmed)
        else:
            formatted_lines.append(trimmed)

    if formatted_lines and all(LIST_ITEM_RE.match(line) for line in formatted_lines):
        return "\n".join(formatted_lines)

    return stripped.replace("\n\n", "\n")


def _convert_table_to_sections(header: list[str], rows: list[list[str]]) -> str:
    sections: list[str] = []

    if len(header) == 1:
        sections.append(f"## {header[0]}\n")
        for row in rows:
            cell = row[0] if row else ""
            sections.append(_format_cell_content(cell))
            sections.append("")
        return "\n".join(sections).strip()

    if len(header) == 2:
        for row in rows:
            title = row[0] if row else "Item"
            body = row[1] if len(row) > 1 else ""
            sections.append(f"## {title}\n")
            formatted = _format_cell_content(body)
            if formatted:
                sections.append(formatted)
            sections.append("\n---\n")
        return "\n".join(sections).strip().rstrip("---").strip()

    sections.append("## Details\n")
    for idx, row in enumerate(rows, start=1):
        title = row[0] if row and row[0].strip() else f"Item {idx}"
        sections.append(f"### {title}\n")
        for col_idx in range(1, len(header)):
            label = header[col_idx]
            value = row[col_idx] if col_idx < len(row) else ""
            if not value.strip():
                continue
            sections.append(f"**{label}**\n")
            sections.append(_format_cell_content(value))
            sections.append("")
        sections.append("---\n")

    result = "\n".join(sections).strip()
    return result.rstrip("-").strip()


def _repair_table_block(block_lines: list[str], stats: FormatStats) -> list[str]:
    parsed = _parse_table_block(block_lines)
    if parsed is None:
        return block_lines

    header, rows = parsed
    col_count = len(header)
    repaired_rows: list[str] = []

    sep = "| " + " | ".join(["---"] * col_count) + " |"
    header_row = "| " + " | ".join(header) + " |"
    repaired_rows.append(header_row)
    repaired_rows.append(sep)

    for row in rows:
        padded = row[:col_count] + [""] * max(0, col_count - len(row))
        repaired_rows.append("| " + " | ".join(padded[:col_count]) + " |")

    stats.tables_repaired += 1
    return repaired_rows


def _process_table_block(block_lines: list[str], stats: FormatStats) -> str | None:
    parsed = _parse_table_block(block_lines)
    if parsed is None:
        return None

    header, rows = parsed
    if _table_needs_conversion(header, rows):
        stats.tables_converted += 1
        return _convert_table_to_sections(header, rows)

    repaired = _repair_table_block(block_lines, stats)
    return "\n".join(repaired)


def _normalize_markdown(content: str) -> str:
    content = re.sub(r"\n{3,}", "\n\n", content)

    lines = content.split("\n")
    result: list[str] = []
    in_list = False
    prev_empty = True

    for line in lines:
        stripped = line.strip()
        is_empty = not stripped
        is_list_item = bool(re.match(r"^(\s*)([-*+]|\d+\.)\s", line))
        is_table = "|" in line and _looks_like_table_row(line)
        is_heading = bool(HEADING_RE.match(stripped))

        if is_heading and result and not prev_empty:
            result.append("")

        if is_list_item and not is_table:
            if not in_list and result and not prev_empty:
                result.append("")
            in_list = True
            result.append(line.rstrip())
        elif in_list and not is_empty and not is_list_item:
            if not prev_empty:
                result.append("")
            in_list = False
            result.append(line.rstrip())
        else:
            if is_empty:
                in_list = False
            result.append(line.rstrip())

        prev_empty = is_empty

    normalized = "\n".join(result)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    # Ensure blank lines around remaining tables
    normalized = _ensure_blank_lines_around_tables(normalized)
    return normalized.strip()


def _ensure_blank_lines_around_tables(content: str) -> str:
    lines = content.split("\n")
    result: list[str] = []
    in_table = False

    for i, line in enumerate(lines):
        is_table = _looks_like_table_row(line) or _is_separator_row(line)
        if is_table and not in_table:
            if result and result[-1].strip():
                result.append("")
            in_table = True
        elif not is_table and in_table:
            if line.strip():
                result.append("")
            in_table = False

        result.append(line)

    return "\n".join(result)
