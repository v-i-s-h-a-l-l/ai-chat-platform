from app.workspace_export.engine import WorkspaceExportEngine
from app.workspace_export.layout.pdf_fonts import has_glyph, pdf_safe_text
from app.workspace_export.models import ExportFormat
from app.workspace_export.pipeline.debug_trace import trace_export_pipeline


PROBLEMATIC = """# Markdown\u00a0to\u00a0PDF

## VS\u202fCode

Take\u2011Home assignment

Case\u2011Study round

In\u2011person interview

command\u2011line tools

- [ ] Pending task
- [x] Completed task
- \u2705 Done task
"""


def test_vera_font_missing_glyph_confirmed():
    assert has_glyph(" ") is True
    assert has_glyph("\u00a0") is True
    assert has_glyph("\u2011") is False  # root cause of Take■Home
    assert has_glyph("\u202f") is False
    assert has_glyph("\u2610") is False


def test_pdf_safe_text_replaces_unsupported_glyphs():
    assert pdf_safe_text("Take\u2011Home") == "Take-Home"
    assert pdf_safe_text("Markdown\u00a0to\u00a0PDF") == "Markdown to PDF"
    assert pdf_safe_text("VS\u202fCode") == "VS Code"
    assert "[x]" in pdf_safe_text("\u2611 done")
    assert "[ ]" in pdf_safe_text("\u2610 todo")


def test_pdf_export_no_black_squares_in_extracted_text():
    engine = WorkspaceExportEngine()
    pdf, _, _ = engine.export(PROBLEMATIC, ExportFormat.PDF, project_name="Demo")
    traces = trace_export_pipeline(PROBLEMATIC, title="glyph-test")
    extracted = traces[-2].sample
    assert "■" not in extracted
    assert "\ufffd" not in extracted
    assert pdf[:4] == b"%PDF"
