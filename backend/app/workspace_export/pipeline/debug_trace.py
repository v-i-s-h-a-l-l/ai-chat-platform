"""Debug utilities for tracing Unicode through the export pipeline."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from app.workspace_export.layout.html_builder import build_html_document
from app.workspace_export.layout.document_layout import render_document_pdf
from app.workspace_export.markdown_parser import parse_markdown
from app.workspace_export.models import ExportMetadata
from app.workspace_export.pipeline.markdown_repair import repair_markdown
from app.workspace_export.pipeline.orchestrator import prepare_export_document
from app.workspace_export.pipeline.unicode_normalizer import normalize_unicode

SUSPICIOUS_CATEGORIES = {"Zs", "Cf", "Zl", "Zp", "Cc"}
SUSPICIOUS_CODEPOINTS = {
    0x00A0, 0x2011, 0x200B, 0x202F, 0x2007, 0x2009, 0x205F, 0xFEFF, 0xFFFC, 0xFFFD,
}


@dataclass
class CharInspection:
    char: str
    codepoint: str
    name: str
    category: str


@dataclass
class StageTrace:
    stage: str
    sample: str
    suspicious_chars: list[CharInspection] = field(default_factory=list)
    has_replacement_glyph: bool = False


def inspect_text(text: str, *, limit: int = 120) -> list[CharInspection]:
    findings: list[CharInspection] = []
    for char in text:
        cp = ord(char)
        if char in "\n\t" or cp < 128 and char.isascii() and char.isprintable() and char not in " \u00a0":
            continue
        if cp in SUSPICIOUS_CODEPOINTS or unicodedata.category(char) in SUSPICIOUS_CATEGORIES:
            findings.append(
                CharInspection(
                    char=char if char not in "\n\t" else repr(char),
                    codepoint=f"U+{cp:04X}",
                    name=unicodedata.name(char, "UNKNOWN"),
                    category=unicodedata.category(char),
                )
            )
    return findings[:limit]


def trace_stage(stage: str, text: str) -> StageTrace:
    return StageTrace(
        stage=stage,
        sample=text[:240].replace("\n", "\\n"),
        suspicious_chars=inspect_text(text),
        has_replacement_glyph="\ufffd" in text or "\ufffc" in text,
    )


def collect_ast_text(document) -> str:
    from app.workspace_export.models import (
        BlockquoteBlock,
        BulletListBlock,
        CodeBlock,
        HeadingBlock,
        ParagraphBlock,
        TableBlock,
    )

    parts: list[str] = []
    for block in document.blocks:
        if isinstance(block, (HeadingBlock, ParagraphBlock)):
            parts.extend(span.text for span in block.spans)
        elif isinstance(block, BulletListBlock):
            for item in block.items:
                parts.extend(span.text for span in item.spans)
        elif isinstance(block, TableBlock):
            for header in block.headers:
                parts.extend(span.text for span in header)
            for row in block.rows:
                for cell in row:
                    parts.extend(span.text for span in cell)
        elif isinstance(block, CodeBlock):
            parts.append(block.code)
        elif isinstance(block, BlockquoteBlock):
            parts.append(collect_ast_text(type(document)(blocks=block.blocks)))
    return " ".join(parts)


def trace_export_pipeline(content: str, *, title: str = "Debug") -> list[StageTrace]:
    traces: list[StageTrace] = []
    traces.append(trace_stage("1_raw_markdown", content))

    repaired = repair_markdown(content)
    traces.append(trace_stage("2_repaired_markdown", repaired))

    normalized_only = normalize_unicode(content)
    traces.append(trace_stage("2b_unicode_normalized_raw", normalized_only))

    prepared = prepare_export_document(content, title=title)
    traces.append(trace_stage("3_prepared_markdown", prepared.markdown))
    traces.append(trace_stage("4_parsed_ast_text", collect_ast_text(prepared.document)))
    traces.append(trace_stage("5_html", prepared.html))

    metadata = ExportMetadata(title=title, project_name="Debug", generated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    pdf_bytes = render_document_pdf(prepared.document, metadata)
    traces.append(trace_stage("6_pdf_binary_length", str(len(pdf_bytes))))

    extracted = extract_pdf_text(pdf_bytes)
    traces.append(trace_stage("7_pdf_extracted_text", extracted))
    traces.append(
        StageTrace(
            stage="7b_pdf_has_black_square",
            sample=extracted[:240],
            suspicious_chars=[],
            has_replacement_glyph="■" in extracted,
        )
    )
    return traces


def extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(pdf_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        return f"<pdf text extraction failed: {exc}>"


def format_trace_report(traces: list[StageTrace]) -> str:
    lines: list[str] = ["Export Pipeline Unicode Trace", "=" * 40]
    for trace in traces:
        lines.append(f"\n[{trace.stage}]")
        lines.append(f"sample: {trace.sample}")
        if trace.has_replacement_glyph:
            lines.append("!! contains ■ or replacement char")
        if trace.suspicious_chars:
            lines.append("suspicious characters:")
            for item in trace.suspicious_chars:
                lines.append(
                    f"  {repr(item.char):6} {item.codepoint} {item.category:3} {item.name}"
                )
        else:
            lines.append("suspicious characters: none")
    return "\n".join(lines)
