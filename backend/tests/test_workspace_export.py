from app.workspace_export.detection import available_formats, detect_export_intent, supports_excel
from app.workspace_export.engine import WorkspaceExportEngine
from app.workspace_export.markdown_parser import parse_markdown
from app.workspace_export.models import ExportFormat


SAMPLE_PLAN = """# MathCo Interview Preparation Plan

## Technical Interview

### Preparation

1. Learn Spark
2. Learn Python
3. Learn ML

---

## Checklist

- ✅ Stable internet
- ✅ Resume ready
"""

SAMPLE_TABLE = """# Interview Schedule

| Stage | Focus | Duration |
| --- | --- | --- |
| Aptitude | Problem solving | 45 min |
| Technical | Data engineering | 60 min |
"""


def test_parse_headings_and_lists():
    doc = parse_markdown(SAMPLE_PLAN)
    assert doc.title == "MathCo Interview Preparation Plan"
    assert len(doc.blocks) >= 4


def test_supports_excel_only_for_tables():
    assert supports_excel(SAMPLE_PLAN) is False
    assert supports_excel(SAMPLE_TABLE) is True


def test_available_formats_includes_excel_for_tables():
    formats = available_formats(SAMPLE_TABLE)
    assert ExportFormat.XLSX in formats
    assert ExportFormat.PDF in formats


def test_detect_export_intent():
    assert detect_export_intent("Download this as PDF") == ExportFormat.PDF
    assert detect_export_intent("Export this to Word") == ExportFormat.DOCX
    assert detect_export_intent("What is Docker?") is None


def test_workspace_export_engine_generates_files():
    engine = WorkspaceExportEngine()
    pdf, pdf_name, pdf_type = engine.export(SAMPLE_PLAN, ExportFormat.PDF, project_name="MathCo")
    docx, docx_name, _ = engine.export(SAMPLE_PLAN, ExportFormat.DOCX, project_name="MathCo")
    md, md_name, _ = engine.export(SAMPLE_PLAN, ExportFormat.MARKDOWN, project_name="MathCo")
    txt, txt_name, _ = engine.export(SAMPLE_PLAN, ExportFormat.TEXT, project_name="MathCo")

    assert pdf_name.endswith(".pdf")
    assert pdf[:4] == b"%PDF"
    assert docx_name.endswith(".docx")
    assert docx[:2] == b"PK"
    assert md_name.endswith(".md")
    assert b"Interview Preparation Plan" in md
    assert txt_name.endswith(".txt")
    assert b"Generated using AI Assistant" in txt
    assert pdf_type == "application/pdf"


def test_workspace_export_engine_generates_xlsx_for_tables():
    engine = WorkspaceExportEngine()
    data, name, media_type = engine.export(
        SAMPLE_TABLE, ExportFormat.XLSX, project_name="MathCo"
    )
    assert name.endswith(".xlsx")
    assert data[:2] == b"PK"
    assert "spreadsheetml" in media_type
