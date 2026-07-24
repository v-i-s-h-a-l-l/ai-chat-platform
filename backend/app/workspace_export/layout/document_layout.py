"""Document layout engine — parsed AST to professional ReportLab flowables."""

from __future__ import annotations

import os
from io import BytesIO

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.workspace_export.layout.pdf_fonts import pdf_safe_text, register_pdf_fonts
from app.workspace_export.layout.print_styles import HEADING_STYLE_MAP
from app.workspace_export.markdown_parser import spans_to_markdown
from app.workspace_export.models import (
    BlockquoteBlock,
    BulletListBlock,
    CodeBlock,
    ExportMetadata,
    HeadingBlock,
    HorizontalRuleBlock,
    InlineSpan,
    ParagraphBlock,
    ParsedDocument,
    TableBlock,
)
from app.workspace_export.pipeline.unicode_normalizer import normalize_unicode

_FONTS_REGISTERED = False


def _register_fonts() -> None:
    global _FONTS_REGISTERED
    register_pdf_fonts()
    _FONTS_REGISTERED = True


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "DocTitle": ParagraphStyle(
            "DocTitle",
            fontName="Vera-Bold",
            fontSize=22,
            leading=27,
            spaceAfter=12,
            textColor=colors.HexColor("#1a1a1a"),
        ),
        "MetaLabel": ParagraphStyle(
            "MetaLabel",
            fontName="Vera-Bold",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#4b5563"),
        ),
        "MetaValue": ParagraphStyle(
            "MetaValue",
            fontName="Vera",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=4,
        ),
        "Heading1": ParagraphStyle(
            "Heading1",
            fontName="Vera-Bold",
            fontSize=18,
            leading=22,
            spaceBefore=16,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "Heading2": ParagraphStyle(
            "Heading2",
            fontName="Vera-Bold",
            fontSize=15,
            leading=19,
            spaceBefore=14,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "Heading3": ParagraphStyle(
            "Heading3",
            fontName="Vera-Bold",
            fontSize=13,
            leading=17,
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "Heading4": ParagraphStyle(
            "Heading4",
            fontName="Vera-Bold",
            fontSize=11.5,
            leading=15,
            spaceBefore=10,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "Body": ParagraphStyle(
            "Body",
            fontName="Vera",
            fontSize=11,
            leading=16,
            spaceAfter=8,
        ),
        "Bullet": ParagraphStyle(
            "Bullet",
            fontName="Vera",
            fontSize=11,
            leading=15,
            leftIndent=18,
            bulletIndent=8,
            spaceAfter=4,
        ),
        "Blockquote": ParagraphStyle(
            "Blockquote",
            fontName="Vera-Italic",
            fontSize=11,
            leading=15,
            leftIndent=16,
            textColor=colors.HexColor("#374151"),
            spaceAfter=8,
        ),
        "Code": ParagraphStyle(
            "Code",
            fontName="VeraMono",
            fontSize=9,
            leading=13,
            backColor=colors.HexColor("#f4f4f5"),
            borderPadding=8,
            spaceAfter=10,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            fontName="Vera",
            fontSize=9,
            leading=12,
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            fontName="Vera-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#1a1a1a"),
        ),
        "Footer": ParagraphStyle(
            "Footer",
            fontName="Vera-Italic",
            fontSize=8,
            textColor=colors.HexColor("#6b7280"),
            spaceBefore=12,
        ),
    }


def render_document_pdf(
    document: ParsedDocument,
    metadata: ExportMetadata,
    *,
    page_size: str = "letter",
) -> bytes:
    _register_fonts()
    styles = _build_styles()
    pagesize = A4 if page_size.lower() == "a4" else letter

    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        topMargin=0.85 * inch,
        bottomMargin=0.9 * inch,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        title=pdf_safe_text(metadata.title),
        author=metadata.platform_name,
    )

    story: list = []
    story.append(Paragraph(_esc(pdf_safe_text(metadata.title)), styles["DocTitle"]))
    story.extend(_metadata_flowables(metadata, styles))
    story.append(Spacer(1, 0.12 * inch))

    skip_title = _normalize_title(metadata.title)
    i = 0
    blocks = document.blocks
    while i < len(blocks):
        block = blocks[i]

        if (
            isinstance(block, HeadingBlock)
            and block.level <= 2
            and _normalize_title(_spans_to_plain(block.spans)) == skip_title
        ):
            i += 1
            continue

        next_block = blocks[i + 1] if i + 1 < len(blocks) else None

        if isinstance(block, HeadingBlock) and isinstance(next_block, BulletListBlock):
            group = _block_to_flowables(block, styles)
            group.extend(_block_to_flowables(next_block, styles))
            if len(next_block.items) <= 12:
                story.append(KeepTogether(group))
            else:
                story.extend(group)
            i += 2
            continue

        flowables = _block_to_flowables(block, styles)
        if isinstance(block, (TableBlock, CodeBlock)) and flowables:
            story.append(KeepTogether(flowables))
        else:
            story.extend(flowables)
        i += 1

    story.append(Paragraph("Generated using AI Assistant", styles["Footer"]))
    pdf.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()


def _metadata_flowables(metadata: ExportMetadata, styles) -> list:
    generated = pdf_safe_text(metadata.generated_at.strftime("%B %d, %Y at %I:%M %p"))
    rows = [
        ("Date:", generated),
    ]
    if metadata.project_name:
        rows.append(("Project:", pdf_safe_text(metadata.project_name)))
    rows.append(("Generated By:", pdf_safe_text(metadata.platform_name)))

    data = []
    for label, value in rows:
        data.append(
            [
                Paragraph(f"<b>{_esc(label)}</b>", styles["MetaLabel"]),
                Paragraph(_esc(value), styles["MetaValue"]),
            ]
        )

    table = Table(data, colWidths=[1.15 * inch, 4.8 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fb")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return [table]


def _block_to_flowables(block, styles) -> list:
    if isinstance(block, HeadingBlock):
        style_name = HEADING_STYLE_MAP.get(min(block.level, 6), "Heading4")
        return [Paragraph(_rich_html(block.spans), styles[style_name])]
    if isinstance(block, ParagraphBlock):
        return [Paragraph(_rich_html(block.spans), styles["Body"])]
    if isinstance(block, BulletListBlock):
        items = []
        for idx, item in enumerate(block.items, start=1):
            if block.ordered:
                prefix = f"{idx}. "
            elif item.checked is True:
                prefix = "[x] "
            elif item.checked is False:
                prefix = "[ ] "
            else:
                prefix = "- "
            body = _rich_html(item.spans)
            items.append(Paragraph(prefix + body, styles["Bullet"]))
        return items
    if isinstance(block, TableBlock):
        return _table_flowables(block, styles)
    if isinstance(block, CodeBlock):
        code = pdf_safe_text(block.code)
        return [Preformatted(code, styles["Code"])]
    if isinstance(block, HorizontalRuleBlock):
        return [
            Spacer(1, 0.06 * inch),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d1d5db")),
            Spacer(1, 0.06 * inch),
        ]
    if isinstance(block, BlockquoteBlock):
        items = []
        for nested in block.blocks:
            for flow in _block_to_flowables(nested, styles):
                if isinstance(flow, Paragraph):
                    flow.style = styles["Blockquote"]
                items.append(flow)
        return items
    return []


def _table_flowables(block: TableBlock, styles) -> list:
    flowables = []
    if block.title:
        flowables.append(Paragraph(_esc(pdf_safe_text(block.title)), styles["Heading3"]))

    header_row = [Paragraph(_rich_html(h), styles["TableHeader"]) for h in block.headers]
    body_rows = [
        [Paragraph(_rich_html(cell), styles["TableCell"]) for cell in row] for row in block.rows
    ]
    data = [header_row, *body_rows]
    col_count = len(block.headers)
    available = 6.8 * inch
    col_width = available / max(col_count, 1)
    table = Table(data, colWidths=[col_width] * col_count, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1a1a1a")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    flowables.append(table)
    flowables.append(Spacer(1, 0.1 * inch))
    return flowables


def _rich_html(spans: list[InlineSpan]) -> str:
    parts: list[str] = []
    for span in spans:
        text = _esc(pdf_safe_text(span.text))
        text = text.replace("\n", "<br/>")
        if span.code:
            text = f'<font face="VeraMono" size="9">{text}</font>'
        if span.bold:
            text = f"<b>{text}</b>"
        if span.italic:
            text = f"<i>{text}</i>"
        if span.link:
            href = _esc(span.link)
            text = f'<a href="{href}" color="#2563eb"><u>{text}</u></a>'
        parts.append(text)
    return "".join(parts)


def _normalize_title(value: str) -> str:
    return " ".join(pdf_safe_text(value).split()).casefold()


def _spans_to_plain(spans: list[InlineSpan]) -> str:
    return "".join(span.text for span in spans)


def _esc(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Vera", 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 0.5 * inch, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()
