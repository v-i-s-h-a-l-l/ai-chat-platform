"""Parse GitHub-Flavored Markdown into a structured document AST."""

from __future__ import annotations

import re

from app.workspace_export.models import (
    BlockquoteBlock,
    BulletListBlock,
    CodeBlock,
    DocumentBlock,
    HeadingBlock,
    HorizontalRuleBlock,
    InlineSpan,
    ListItem,
    ParagraphBlock,
    ParsedDocument,
    TableBlock,
)
from app.workspace_export.pipeline.table_repair import (
    is_separator_row,
    looks_like_table_row,
    split_table_cells,
)

_INLINE_PATTERN = re.compile(
    r"(\*\*.+?\*\*|\*.+?\*|`[^`]+`|\[[^\]]+\]\([^)]+\))"
)
_LINK_PATTERN = re.compile(r"^\[(.+?)\]\((.+?)\)$")
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")
_ORDERED_ITEM_PATTERN = re.compile(r"^(\d+)\.\s+(.+)$")
_BULLET_ITEM_PATTERN = re.compile(r"^(\s*)[-*+]\s+(.+)$")
_CHECKBOX_PATTERN = re.compile(r"^\[( |x|X)\]\s*(.*)$")
_HR_PATTERN = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
_TABLE_SEPARATOR_PATTERN = re.compile(r"^\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)+\|?\s*$")


def parse_markdown(content: str) -> ParsedDocument:
    lines = content.replace("\r\n", "\n").split("\n")
    blocks: list[DocumentBlock] = []
    i = 0
    title: str | None = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("```"):
            code_lines: list[str] = []
            language = stripped[3:].strip()
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append(CodeBlock(language=language, code="\n".join(code_lines)))
            i += 1
            continue

        if _HR_PATTERN.match(stripped):
            blocks.append(HorizontalRuleBlock())
            i += 1
            continue

        heading_match = _HEADING_PATTERN.match(stripped)
        if heading_match:
            level = len(heading_match.group(1))
            spans = _parse_inline(heading_match.group(2))
            blocks.append(HeadingBlock(level=level, spans=spans))
            if title is None and level <= 2:
                title = _spans_to_plain(spans)
            i += 1
            continue

        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            nested = parse_markdown("\n".join(quote_lines))
            blocks.append(BlockquoteBlock(blocks=nested.blocks))
            continue

        if looks_like_table_row(stripped) and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if is_separator_row(next_line) or (
                looks_like_table_row(next_line) and not _HEADING_PATTERN.match(next_line)
            ):
                table, consumed = _parse_table(lines[i:])
                blocks.append(table)
                i += consumed
                continue

        if _ORDERED_ITEM_PATTERN.match(stripped) or _BULLET_ITEM_PATTERN.match(line):
            list_block, consumed = _parse_list(lines[i:])
            blocks.append(list_block)
            i += consumed
            continue

        para_lines: list[str] = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (
                not nxt
                or nxt.startswith("```")
                or _HEADING_PATTERN.match(nxt)
                or _HR_PATTERN.match(nxt)
                or nxt.startswith(">")
                or looks_like_table_row(nxt)
                or _ORDERED_ITEM_PATTERN.match(nxt)
                or _BULLET_ITEM_PATTERN.match(lines[i])
            ):
                break
            para_lines.append(nxt)
            i += 1
        blocks.append(ParagraphBlock(spans=_parse_inline(" ".join(para_lines))))

    return ParsedDocument(blocks=blocks, title=title)


def _parse_table(lines: list[str]) -> tuple[TableBlock, int]:
    headers = [_parse_inline(cell) for cell in split_table_cells(lines[0])]
    i = 1
    if i < len(lines) and is_separator_row(lines[i].strip()):
        i = 2

    rows: list[list[list[InlineSpan]]] = []
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            break

        if is_separator_row(stripped):
            i += 1
            continue

        if stripped.startswith("|") or (
            looks_like_table_row(stripped)
            and len(split_table_cells(stripped)) >= max(1, len(headers) - 1)
        ):
            rows.append([_parse_inline(cell) for cell in split_table_cells(stripped)])
            i += 1
            continue

        if rows:
            continuation = stripped.rstrip("|").strip()
            last_cell = rows[-1][-1]
            merged = _spans_to_plain(last_cell) + "\n" + continuation
            rows[-1][-1] = _parse_inline(merged.strip())
            i += 1
            continue

        break

    return TableBlock(headers=headers, rows=rows), i


def _looks_like_table_row(line: str) -> bool:
    return looks_like_table_row(line)


def _parse_list(lines: list[str]) -> tuple[BulletListBlock, int]:
    ordered = bool(_ORDERED_ITEM_PATTERN.match(lines[0].strip()))
    items: list[ListItem] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            break

        ordered_match = _ORDERED_ITEM_PATTERN.match(stripped)
        bullet_match = _BULLET_ITEM_PATTERN.match(raw)
        if not ordered_match and not bullet_match:
            break
        if ordered_match and not ordered:
            break
        if bullet_match and ordered:
            if items and bullet_match.group(1):
                sub_text = bullet_match.group(2)
                previous = items[-1]
                merged = _spans_to_plain(previous.spans) + "\n- " + sub_text
                items[-1] = ListItem(spans=_parse_inline(merged), checked=previous.checked)
                i += 1
                continue
            break

        text = ordered_match.group(2) if ordered_match else bullet_match.group(2)
        checked: bool | None = None
        checkbox = _CHECKBOX_PATTERN.match(text)
        if checkbox:
            checked = checkbox.group(1).lower() == "x"
            text = checkbox.group(2)
        elif text.startswith("✅"):
            checked = True
            text = text[1:].strip()
        elif text.startswith("☐") or text.startswith("☑"):
            checked = text.startswith("☑")
            text = text[1:].strip()

        items.append(ListItem(spans=_parse_inline(text), checked=checked))
        i += 1

    return BulletListBlock(items=items, ordered=ordered), i


def _parse_inline(text: str) -> list[InlineSpan]:
    if not text:
        return [InlineSpan(text="")]

    spans: list[InlineSpan] = []
    pos = 0
    for match in _INLINE_PATTERN.finditer(text):
        if match.start() > pos:
            spans.append(InlineSpan(text=text[pos : match.start()]))
        token = match.group(0)
        if token.startswith("**") and token.endswith("**"):
            spans.append(InlineSpan(text=token[2:-2], bold=True))
        elif token.startswith("*") and token.endswith("*"):
            spans.append(InlineSpan(text=token[1:-1], italic=True))
        elif token.startswith("`") and token.endswith("`"):
            spans.append(InlineSpan(text=token[1:-1], code=True))
        else:
            link_match = _LINK_PATTERN.match(token)
            if link_match:
                spans.append(InlineSpan(text=link_match.group(1), link=link_match.group(2)))
            else:
                spans.append(InlineSpan(text=token))
        pos = match.end()

    if pos < len(text):
        spans.append(InlineSpan(text=text[pos:]))

    return spans or [InlineSpan(text=text)]


def _spans_to_plain(spans: list[InlineSpan]) -> str:
    return "".join(span.text for span in spans)


def spans_to_markdown(spans: list[InlineSpan]) -> str:
    parts: list[str] = []
    for span in spans:
        text = span.text
        if span.link:
            text = f"[{text}]({span.link})"
        if span.code:
            text = f"`{text}`"
        if span.bold:
            text = f"**{text}**"
        if span.italic:
            text = f"*{text}*"
        parts.append(text)
    return "".join(parts)


def document_to_markdown(doc: ParsedDocument) -> str:
    lines: list[str] = []
    for block in doc.blocks:
        if isinstance(block, HeadingBlock):
            lines.append(f"{'#' * block.level} {spans_to_markdown(block.spans)}")
        elif isinstance(block, ParagraphBlock):
            lines.append(spans_to_markdown(block.spans))
        elif isinstance(block, BulletListBlock):
            for idx, item in enumerate(block.items, start=1):
                prefix = f"{idx}. " if block.ordered else "- "
                if item.checked is True:
                    prefix = "- ✅ "
                elif item.checked is False:
                    prefix = "- ☐ "
                lines.append(f"{prefix}{spans_to_markdown(item.spans)}")
        elif isinstance(block, TableBlock):
            if block.title:
                lines.append(f"### {block.title}")
            header = "| " + " | ".join(spans_to_markdown(h) for h in block.headers) + " |"
            sep = "| " + " | ".join(["---"] * len(block.headers)) + " |"
            lines.append(header)
            lines.append(sep)
            for row in block.rows:
                lines.append("| " + " | ".join(spans_to_markdown(cell) for cell in row) + " |")
        elif isinstance(block, CodeBlock):
            lines.append(f"```{block.language}")
            lines.append(block.code)
            lines.append("```")
        elif isinstance(block, HorizontalRuleBlock):
            lines.append("---")
        elif isinstance(block, BlockquoteBlock):
            nested = document_to_markdown(ParsedDocument(blocks=block.blocks))
            lines.extend(f"> {line}" for line in nested.split("\n"))
        lines.append("")
    return "\n".join(lines).strip()
