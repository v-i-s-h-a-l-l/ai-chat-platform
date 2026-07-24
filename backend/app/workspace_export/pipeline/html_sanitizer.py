"""HTML sanitization for the export pipeline."""

from __future__ import annotations

import re

_RAW_TAG_RE = re.compile(r"<[^>]+>")


def sanitize_html(html: str) -> str:
    """Remove unsafe or leaked raw HTML while preserving semantic structure."""
    if not html:
        return html

    # Allow only a safe subset used by our layout builder.
    allowed = ("p", "h1", "h2", "h3", "h4", "strong", "em", "code", "a", "ul", "ol", "li",
               "table", "thead", "tbody", "tr", "th", "td", "blockquote", "pre", "hr",
               "div", "span", "br", "img")

    def strip_disallowed(match: re.Match[str]) -> str:
        tag = match.group(0)
        name_match = re.match(r"</?\s*([a-zA-Z0-9]+)", tag)
        if not name_match:
            return ""
        name = name_match.group(1).lower()
        if name in allowed:
            return tag
        return ""

    cleaned = re.sub(r"<[^>]+>", strip_disallowed, html)
    cleaned = cleaned.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    return cleaned


def contains_raw_html_leak(text: str) -> bool:
    """Detect raw HTML that should not appear in final output."""
    if _RAW_TAG_RE.search(text):
        # Our builder emits intentional tags — flag common leak patterns only.
        leaks = re.findall(r"<\s*br\s*/?\s*>|</?(?:div|span|p)\b", text, flags=re.IGNORECASE)
        return bool(leaks)
    return False
