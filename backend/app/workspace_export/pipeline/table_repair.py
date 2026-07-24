"""Repair and normalize AI-generated markdown tables before export parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass

LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|(?:\d+\.))\s", re.MULTILINE)
SEPARATOR_ROW_RE = re.compile(r"^\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")
NEW_ROW_BOLD_RE = re.compile(r"^\*\*.+\*\*\s*$")
SCHEDULE_DAY_RE = re.compile(r"^\d{1,2}(?:-\d{1,2})?$")
MAX_CELL_LINES = 3
MAX_CELL_CHARS = 150


@dataclass
class TableRepairStats:
    tables_converted: int = 0
    tables_repaired: int = 0


def repair_tables(content: str) -> str:
    """Convert or repair markdown tables so export renderers receive clean structure."""
    if not content or not content.strip():
        return content

    stats = TableRepairStats()
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

    return _ensure_blank_lines_around_tables("\n".join(output))


def looks_like_table_row(line: str) -> bool:
    trimmed = line.strip()
    if not trimmed or trimmed.startswith("```"):
        return False
    return "|" in trimmed


def is_separator_row(line: str) -> bool:
    trimmed = line.strip().replace("||", "|")
    if "-" not in trimmed:
        return False
    return bool(SEPARATOR_ROW_RE.match(trimmed))


def split_table_cells(line: str) -> list[str]:
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
    return [_clean_table_cell(cell) for cell in cells]


def _clean_table_cell(cell: str) -> str:
    return cell.strip().rstrip("|").strip()


def _is_table_continuation(line: str, rows: list[list[str]]) -> bool:
    if not rows:
        return False
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("|"):
        return False
    if is_separator_row(stripped):
        return False
    if NEW_ROW_BOLD_RE.match(stripped):
        return False
    if "|" in stripped:
        cells = split_table_cells(stripped if stripped.startswith("|") else f"|{stripped}")
        if len(cells) >= 2 and any(cells):
            return False
    if LIST_ITEM_RE.match(stripped):
        return True
    if re.match(r"^\s+[-*+•]\s", line):
        return True
    if stripped.endswith("|"):
        return True
    return False


def _find_table_block_end(lines: list[str], start: int) -> int | None:
    if not looks_like_table_row(lines[start]):
        return None

    end = start + 1
    while end < len(lines):
        line = lines[end]
        if not line.strip():
            peek = end + 1
            while peek < len(lines) and not lines[peek].strip():
                peek += 1
            if peek < len(lines) and (
                looks_like_table_row(lines[peek]) or is_separator_row(lines[peek].strip())
            ):
                end = peek
                continue
            break
        if looks_like_table_row(line) or is_separator_row(line):
            end += 1
            continue
        if end > start + 1:
            end += 1
            continue
        break

    if end - start < 2:
        return None
    return end


def _parse_table_block(block_lines: list[str]) -> tuple[list[str], list[list[str]]] | None:
    non_empty = [line for line in block_lines if line.strip()]
    if len(non_empty) < 2:
        return None

    header = split_table_cells(non_empty[0])
    if not header or all(not cell for cell in header):
        return None

    data_start = 1
    if len(non_empty) > 1 and is_separator_row(non_empty[1]):
        data_start = 2

    rows: list[list[str]] = []
    for line in non_empty[data_start:]:
        if is_separator_row(line):
            continue

        stripped = line.strip()
        if stripped.startswith("|") or (
            looks_like_table_row(line)
            and len(split_table_cells(stripped if stripped.startswith("|") else f"|{stripped}"))
            >= max(2, len(header) - 1)
            and not _is_table_continuation(line, rows)
        ):
            row_line = stripped if stripped.startswith("|") else f"|{stripped}"
            rows.append(split_table_cells(row_line))
            continue

        if _is_table_continuation(line, rows):
            continuation = stripped.rstrip("|").strip()
            rows[-1][-1] = f"{rows[-1][-1]}\n{continuation}".strip()
            continue

        if NEW_ROW_BOLD_RE.match(stripped):
            rows.append([stripped, ""])
            continue

        rows.append(split_table_cells(stripped if stripped.startswith("|") else f"|{stripped}"))

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

    non_empty = [line for line in stripped.split("\n") if line.strip()]
    if len(non_empty) > MAX_CELL_LINES:
        return True
    if LIST_ITEM_RE.search(stripped):
        return True
    return False


def _is_schedule_table(header: list[str], rows: list[list[str]]) -> bool:
    if len(header) != 3:
        return False
    header_lower = [cell.strip().lower() for cell in header]
    if header_lower[0] != "day" or header_lower[1] != "focus" or header_lower[2] != "activity":
        return False
    return all(
        SCHEDULE_DAY_RE.match((row[0] if row else "").strip())
        for row in rows
        if row and row[0].strip()
    )


def _table_needs_conversion(header: list[str], rows: list[list[str]]) -> bool:
    if _is_schedule_table(header, rows):
        return False

    for cell in header:
        if _cell_violates(cell):
            return True
    for row in rows:
        for cell in row:
            if _cell_violates(cell):
                return True

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
        formatted_lines.append(trimmed)

    if formatted_lines and all(LIST_ITEM_RE.match(line) for line in formatted_lines):
        return "\n".join(formatted_lines)

    return stripped.replace("\n\n", "\n")


def _strip_bold_markers(text: str) -> str:
    stripped = text.strip()
    match = re.match(r"^\*\*(.+)\*\*$", stripped)
    return match.group(1) if match else stripped


def _convert_table_to_sections(header: list[str], rows: list[list[str]]) -> str:
    sections: list[str] = []

    if len(header) == 1:
        sections.append(f"## {_strip_bold_markers(header[0])}\n")
        for row in rows:
            cell = row[0] if row else ""
            sections.append(_format_cell_content(cell))
            sections.append("")
        return "\n".join(sections).strip()

    if len(header) == 2:
        for row in rows:
            title = _strip_bold_markers(row[0] if row else "Item")
            body = row[1] if len(row) > 1 else ""
            sections.append(f"## {title}\n")
            formatted = _format_cell_content(body)
            if formatted:
                sections.append(formatted)
            sections.append("\n---\n")
        return "\n".join(sections).strip().rstrip("---").strip()

    for idx, row in enumerate(rows, start=1):
        raw_title = row[0] if row and row[0].strip() else f"Item {idx}"
        title = _strip_bold_markers(raw_title)
        sections.append(f"### {title}\n")
        for col_idx in range(1, len(header)):
            label = _strip_bold_markers(header[col_idx])
            value = row[col_idx] if col_idx < len(row) else ""
            if not value.strip():
                continue
            sections.append(f"**{label}**\n")
            sections.append(_format_cell_content(value))
            sections.append("")
        sections.append("---\n")

    result = "\n".join(sections).strip()
    return result.rstrip("-").strip()


def _repair_table_block(block_lines: list[str], stats: TableRepairStats) -> list[str]:
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


def _process_table_block(block_lines: list[str], stats: TableRepairStats) -> str | None:
    parsed = _parse_table_block(block_lines)
    if parsed is None:
        return None

    header, rows = parsed
    if _table_needs_conversion(header, rows):
        stats.tables_converted += 1
        return _convert_table_to_sections(header, rows)

    repaired = _repair_table_block(block_lines, stats)
    return "\n".join(repaired)


def _ensure_blank_lines_around_tables(content: str) -> str:
    lines = content.split("\n")
    result: list[str] = []
    in_table = False

    for line in lines:
        is_table = looks_like_table_row(line) or is_separator_row(line)
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
