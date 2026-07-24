"""PDF font registration and glyph-safe text handling."""

from __future__ import annotations

import os
import unicodedata

import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.workspace_export.pipeline.unicode_normalizer import normalize_unicode

_FONTS_READY = False
_VERA_FACE = None

# Characters we intentionally substitute before PDF rendering when missing from Vera.
_ASCII_FALLBACKS = {
    "\u2022": "-",   # bullet (Vera has glyph, but lists use ASCII prefix)
    "\u2610": "[ ]",
    "\u2611": "[x]",
    "\u2705": "[x]",
}


def register_pdf_fonts() -> None:
    global _FONTS_READY, _VERA_FACE
    if _FONTS_READY:
        return

    font_dir = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
    pdfmetrics.registerFont(TTFont("Vera", os.path.join(font_dir, "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("Vera-Bold", os.path.join(font_dir, "VeraBd.ttf")))
    pdfmetrics.registerFont(TTFont("Vera-Italic", os.path.join(font_dir, "VeraIt.ttf")))
    pdfmetrics.registerFont(TTFont("Vera-BoldItalic", os.path.join(font_dir, "VeraBI.ttf")))
    pdfmetrics.registerFontFamily(
        "Vera",
        normal="Vera",
        bold="Vera-Bold",
        italic="Vera-Italic",
        boldItalic="Vera-BoldItalic",
    )
    pdfmetrics.registerFont(TTFont("VeraMono", os.path.join(font_dir, "Vera.ttf")))

    _VERA_FACE = pdfmetrics.getFont("Vera").face
    _FONTS_READY = True


def get_vera_face():
    register_pdf_fonts()
    return _VERA_FACE


def has_glyph(char: str) -> bool:
    face = get_vera_face()
    return face.charToGlyph.get(ord(char)) is not None


def pdf_safe_text(text: str) -> str:
    """
    Final gate before ReportLab rendering.

    1. Unicode normalization (NBSP, NB-hyphen, ZW chars, etc.)
    2. Font-aware filtering — any character Vera cannot render is replaced
       with an ASCII-safe alternative (never pass through to the PDF renderer).
    """
    if not text:
        return text

    normalized = normalize_unicode(text)
    face = get_vera_face()
    output: list[str] = []

    for char in normalized:
        if char in _ASCII_FALLBACKS:
            output.append(_ASCII_FALLBACKS[char])
            continue

        if ord(char) < 128 or face.charToGlyph.get(ord(char)) is not None:
            output.append(char)
            continue

        category = unicodedata.category(char)
        if category == "Zs":
            output.append(" ")
        elif category in {"Pd", "Pc"}:
            output.append("-")
        elif category == "Pi" or category == "Pf":
            output.append('"')
        elif category == "Po" and char in "•·":
            output.append("-")
        # Drop other unsupported symbols rather than render ■
        elif category != "Cf":
            output.append("")

    return "".join(output)
