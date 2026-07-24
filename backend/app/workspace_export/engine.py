from __future__ import annotations

from datetime import datetime, timezone

from app.workspace_export.detection import available_formats, supports_excel
from app.workspace_export.filename import build_filename
from app.workspace_export.markdown_parser import parse_markdown
from app.workspace_export.models import ExportFormat, ExportMetadata
from app.workspace_export.renderers.docx_renderer import render_docx
from app.workspace_export.renderers.markdown_renderer import render_markdown
from app.workspace_export.renderers.pdf_renderer import render_pdf
from app.workspace_export.renderers.text_renderer import render_text
from app.workspace_export.renderers.xlsx_renderer import render_xlsx


class WorkspaceExportEngine:
    """Render already-generated chat responses into downloadable workspace documents."""

    MEDIA_TYPES = {
        ExportFormat.PDF: "application/pdf",
        ExportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ExportFormat.MARKDOWN: "text/markdown; charset=utf-8",
        ExportFormat.TEXT: "text/plain; charset=utf-8",
    }

    def list_formats(self, content: str) -> list[str]:
        return [fmt.value for fmt in available_formats(content)]

    def supports_excel(self, content: str) -> bool:
        return supports_excel(content)

    def export(
        self,
        content: str,
        export_format: ExportFormat,
        *,
        project_name: str | None = None,
        title: str | None = None,
    ) -> tuple[bytes, str, str]:
        if export_format == ExportFormat.XLSX and not supports_excel(content):
            raise ValueError("Excel export requires tabular content in the response")

        metadata = self._build_metadata(content, project_name=project_name, title=title)
        data = self._render(content, export_format, metadata)
        filename = build_filename(content, export_format, project_name=project_name)
        media_type = self.MEDIA_TYPES[export_format]
        return data, filename, media_type

    def _build_metadata(
        self,
        content: str,
        *,
        project_name: str | None,
        title: str | None,
    ) -> ExportMetadata:
        doc = parse_markdown(content)
        resolved_title = title or doc.title or project_name or "AI Response"
        return ExportMetadata(
            title=resolved_title,
            project_name=project_name,
            generated_at=datetime.now(timezone.utc),
        )

    def _render(self, content: str, export_format: ExportFormat, metadata: ExportMetadata) -> bytes:
        if export_format == ExportFormat.PDF:
            return render_pdf(content, metadata)
        if export_format == ExportFormat.DOCX:
            return render_docx(content, metadata)
        if export_format == ExportFormat.XLSX:
            return render_xlsx(content, metadata)
        if export_format == ExportFormat.MARKDOWN:
            return render_markdown(content, metadata).encode("utf-8")
        if export_format == ExportFormat.TEXT:
            doc = parse_markdown(content)
            return render_text(doc, metadata).encode("utf-8")
        raise ValueError(f"Unsupported export format: {export_format}")
