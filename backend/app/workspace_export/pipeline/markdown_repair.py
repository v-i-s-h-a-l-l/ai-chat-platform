"""Repair AI-generated markdown before export rendering."""

from __future__ import annotations

import re

from app.workspace_export.pipeline.table_repair import repair_tables
from app.workspace_export.pipeline.unicode_normalizer import normalize_unicode

_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_TAG_RE = re.compile(r"</?(?:b|strong|i|em|u|p|div|span|h[1-6])\s*/?>", re.IGNORECASE)
_STRIP_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")
_CHECKBOX_MD_RE = re.compile(r"^(\s*)[-*+]\s+\[( |x|X)\]\s+", re.MULTILINE)
_HEADING_BOLD_RE = re.compile(r"^(#{1,6})\s+\*\*(.+?)\*\*\s*$", re.MULTILINE)
_ERRONEOUS_NUMBERED_HEADING_RE = re.compile(r"^## (\d+\.\s)", re.MULTILINE)


def repair_markdown(content: str) -> str:
    """Return clean GitHub-Flavored Markdown suitable for export."""
    if not content:
        return content

    text = normalize_unicode(content)
    text = _convert_html_to_markdown(text)
    text = repair_tables(text)
    text = _normalize_checkboxes(text)
    text = _normalize_headings(text)
    text = _indent_nested_list_items(text)
    text = _normalize_horizontal_rules(text)
    text = _MULTI_BLANK_RE.sub("\n\n", text)
    text = normalize_unicode(text)
    return text.strip()


def _normalize_headings(text: str) -> str:
    text = _HEADING_BOLD_RE.sub(r"\1 \2", text)
    text = _ERRONEOUS_NUMBERED_HEADING_RE.sub(r"\1", text)
    return text


def _convert_html_to_markdown(text: str) -> str:
    # Use single newlines for <br> so inline table cell breaks stay on one row.
    text = _BR_RE.sub("\n", text)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p\s*>", "", text, flags=re.IGNORECASE)
    text = text.replace("<strong>", "**").replace("</strong>", "**")
    text = text.replace("<b>", "**").replace("</b>", "**")
    text = text.replace("<em>", "*").replace("</em>", "*")
    text = text.replace("<i>", "*").replace("</i>", "*")
    text = _TAG_RE.sub("", text)
    text = _STRIP_TAG_RE.sub("", text)
    return text


def _normalize_checkboxes(text: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        indent, state = match.group(1), match.group(2)
        marker = "✅" if state.lower() == "x" else "☐"
        return f"{indent}- {marker} "

    return _CHECKBOX_MD_RE.sub(replacer, text)


def _indent_nested_list_items(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    in_sublist = False

    for line in lines:
        stripped = line.strip()
        if re.match(r"^\d+\.\s", stripped):
            in_sublist = False
            result.append(line)
            continue

        if stripped.startswith(("-", "*", "+")):
            if in_sublist or (result and re.match(r"^\d+\.\s", result[-1].strip())):
                result.append(f"   {stripped}")
                in_sublist = True
                continue

        in_sublist = False
        result.append(line)

    return "\n".join(result)


def _normalize_horizontal_rules(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    last_was_hr = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            if not last_was_hr:
                result.append("---")
                last_was_hr = True
            continue
        last_was_hr = False
        result.append(line)
    return "\n".join(result)
