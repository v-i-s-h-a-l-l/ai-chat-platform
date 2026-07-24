"""Unicode normalization for PDF-safe, clean UTF-8 text."""

from __future__ import annotations

import re
import unicodedata

# Characters that often render as ■ in standard PDF fonts when not normalized.
_REPLACEMENTS: dict[str, str] = {
    "\u00a0": " ",   # non-breaking space
    "\u2009": " ",   # thin space
    "\u200a": " ",   # hair space
    "\u205f": " ",   # medium mathematical space
    "\u3000": " ",   # ideographic space
    "\u2007": " ",   # figure space
    "\u2011": "-",   # non-breaking hyphen
    "\u2010": "-",   # hyphen
    "\u2012": "-",   # figure dash
    "\u2013": "-",   # en dash
    "\u2014": "-",   # em dash
    "\u2212": "-",   # minus sign
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201a": "'",   # single low quote
    "\u201b": "'",   # single high reversed quote
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u201e": '"',   # double low quote
    "\u2032": "'",   # prime
    "\u2033": '"',   # double prime
    "\u2022": "-",   # bullet (lists handled separately in markdown)
    "\u2023": "-",
    "\u2043": "-",
    "\u25aa": "-",
    "\u25cf": "-",
    "\u25cb": "-",
    "\u25e6": "-",
    "\u2044": "/",   # fraction slash
    "\u2192": "->",  # right arrow
    "\u2190": "<-",  # left arrow
    "\u00ad": "",    # soft hyphen
    "\u200b": "",    # zero-width space
    "\u200c": "",    # zero-width non-joiner
    "\u200d": "",    # zero-width joiner
    "\u2060": "",    # word joiner
    "\ufeff": "",    # BOM
    "\u00b7": "-",   # middle dot
}

# Private-use / replacement glyphs that must never reach the renderer.
_FORBIDDEN_RE = re.compile(r"[\ufffd\uFFFC]")
_CITATION_MARKER_RE = re.compile(r"【[^】]*】")


def normalize_unicode(text: str) -> str:
    """Convert problematic Unicode into clean, PDF-safe UTF-8 text."""
    if not text:
        return text

    normalized = unicodedata.normalize("NFKC", text)

    for source, target in _REPLACEMENTS.items():
        normalized = normalized.replace(source, target)

    # Collapse exotic whitespace to a regular space.
    normalized = re.sub(r"[^\S\n\t]+", " ", normalized)

    # Strip invisible formatting characters (Unicode category Cf) except newline/tab.
    cleaned: list[str] = []
    for char in normalized:
        if char in "\n\t":
            cleaned.append(char)
            continue
        if unicodedata.category(char) == "Cf":
            continue
        cleaned.append(char)

    result = "".join(cleaned)
    result = _FORBIDDEN_RE.sub("", result)
    result = _CITATION_MARKER_RE.sub("", result)
    return result.strip() if text == text.strip() else result
