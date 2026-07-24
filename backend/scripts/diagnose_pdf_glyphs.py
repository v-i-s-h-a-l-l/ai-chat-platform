"""Diagnose ReportLab glyph rendering for Unicode edge cases."""

from __future__ import annotations

import os
import sys
from io import BytesIO

import reportlab
from pypdf import PdfReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.workspace_export.pipeline.debug_trace import format_trace_report, trace_export_pipeline
from app.workspace_export.pipeline.unicode_normalizer import normalize_unicode

font_dir = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
pdfmetrics.registerFont(TTFont("Vera", os.path.join(font_dir, "Vera.ttf")))
pdfmetrics.registerFont(TTFont("Vera-Bold", os.path.join(font_dir, "VeraBd.ttf")))
pdfmetrics.registerFontFamily("Vera", normal="Vera", bold="Vera-Bold", italic="Vera", boldItalic="Vera-Bold")


def render_paragraph(text: str, *, font: str = "Vera", bold: bool = False) -> str:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=(400, 200))
    style = ParagraphStyle("s", fontName=font, fontSize=12, leading=14)
    payload = f"<b>{text}</b>" if bold else text
    doc.build([Paragraph(payload, style)])
    return (PdfReader(buf).pages[0].extract_text() or "").replace("\n", " ")


def main() -> None:
    print("=== ReportLab direct glyph tests ===")
    cases = [
        ("Vera+ascii", "Take Home", "Vera", False),
        ("Vera+nbsp", "Take\u00a0Home", "Vera", False),
        ("Vera+nbhyphen", "Take\u2011Home", "Vera", False),
        ("Vera+bullet", "\u2022 item", "Vera", False),
        ("Vera+checkbox", "\u2610 task \u2611 done", "Vera", False),
        ("Helvetica+nbsp", "Take\u00a0Home", "Helvetica", False),
        ("Vera+b+nbsp", "Take\u00a0Home", "Vera", True),
        ("Vera+b+nbhyphen", "Take\u2011Home", "Vera", True),
    ]
    for name, text, font, bold in cases:
        extracted = render_paragraph(text, font=font, bold=bold)
        has_square = "\u25a0" in extracted or "■" in extracted
        print(f"{name}: {extracted!r} square={has_square}")

    print("\n=== Normalized vs raw in Vera ===")
    raw = "Markdown\u00a0to\u00a0PDF"
    norm = normalize_unicode(raw)
    print(f"raw render:  {render_paragraph(raw)!r}")
    print(f"norm render: {render_paragraph(norm)!r}")

    print("\n=== Full pipeline trace (NBSP sample) ===")
    sample = "Markdown\u00a0to\u00a0PDF\n\nVS\u00a0Code\n\nTake\u00a0Home"
    print(format_trace_report(trace_export_pipeline(sample, title="diag")))

    print("\n=== Full pipeline trace (NBHYPHEN sample, skip repair?) ===")
    sample2 = "Take\u2011Home\n\nCase\u2011Study\n\ncommand\u2011line"
    print(format_trace_report(trace_export_pipeline(sample2, title="diag2")))


if __name__ == "__main__":
    main()
