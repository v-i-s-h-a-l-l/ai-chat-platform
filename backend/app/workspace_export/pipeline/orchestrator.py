"""Orchestrates the export preprocessing pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from app.workspace_export.markdown_parser import parse_markdown
from app.workspace_export.models import ParsedDocument
from app.workspace_export.pipeline.document_normalizer import normalize_document
from app.workspace_export.pipeline.markdown_repair import repair_markdown
from app.workspace_export.pipeline.validator import filter_horizontal_rules, validate_export_document
from app.workspace_export.layout.html_builder import build_html_document


@dataclass(frozen=True)
class PreparedExportDocument:
    markdown: str
    document: ParsedDocument
    html: str


def prepare_export_document(content: str, *, title: str | None = None) -> PreparedExportDocument:
    """
    Markdown Repair → Unicode Normalization → Parse → Validate → HTML Layout.
    """
    repaired = repair_markdown(content)
    document = normalize_document(parse_markdown(repaired))
    document = filter_horizontal_rules(document)
    html = build_html_document(document, title=title or document.title)
    validate_export_document(repaired, document, html)
    return PreparedExportDocument(markdown=repaired, document=document, html=html)
