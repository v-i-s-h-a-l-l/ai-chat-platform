from __future__ import annotations

from app.workspace_export.layout.document_layout import render_document_pdf
from app.workspace_export.models import ExportMetadata
from app.workspace_export.pipeline.orchestrator import prepare_export_document


def render_pdf(content: str, metadata: ExportMetadata, *, page_size: str = "letter") -> bytes:
    """
    Professional PDF export pipeline:

    Markdown Repair → Unicode Normalization → Parse → Validate → Layout → PDF
    """
    prepared = prepare_export_document(content, title=metadata.title)
    return render_document_pdf(prepared.document, metadata, page_size=page_size)
