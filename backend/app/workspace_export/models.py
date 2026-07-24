from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ExportFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    MARKDOWN = "md"
    TEXT = "txt"


@dataclass
class InlineSpan:
    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False
    link: str | None = None


@dataclass
class ListItem:
    spans: list[InlineSpan]
    checked: bool | None = None
    children: list[ListItem] = field(default_factory=list)


@dataclass
class ParagraphBlock:
    spans: list[InlineSpan]


@dataclass
class HeadingBlock:
    level: int
    spans: list[InlineSpan]


@dataclass
class BulletListBlock:
    items: list[ListItem]
    ordered: bool = False


@dataclass
class TableBlock:
    headers: list[list[InlineSpan]]
    rows: list[list[list[InlineSpan]]]
    title: str | None = None


@dataclass
class CodeBlock:
    language: str
    code: str


@dataclass
class BlockquoteBlock:
    blocks: list[DocumentBlock]


@dataclass
class HorizontalRuleBlock:
    pass


DocumentBlock = (
    ParagraphBlock
    | HeadingBlock
    | BulletListBlock
    | TableBlock
    | CodeBlock
    | BlockquoteBlock
    | HorizontalRuleBlock
)


@dataclass
class ParsedDocument:
    blocks: list[DocumentBlock]
    title: str | None = None


@dataclass
class ExportMetadata:
    title: str
    project_name: str | None
    generated_at: datetime
    platform_name: str = "AI Platform"
