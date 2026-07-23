"""Remove duplicate and boilerplate content from retrieved chunks."""

import logging
import re
import time

from app.providers.types import RetrievedChunk

logger = logging.getLogger(__name__)

BOILERPLATE_PATTERNS = [
    re.compile(r"^page \d+ of \d+$", re.IGNORECASE),
    re.compile(r"^copyright", re.IGNORECASE),
    re.compile(r"^all rights reserved", re.IGNORECASE),
]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _is_boilerplate(text: str) -> bool:
    for pattern in BOILERPLATE_PATTERNS:
        if pattern.match(text.strip()):
            return True
    return len(text.strip()) < 20


def compress_context(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    t0 = time.perf_counter()
    seen: set[str] = set()
    result: list[RetrievedChunk] = []

    for chunk in chunks:
        if _is_boilerplate(chunk.content):
            continue
        normalized = _normalize(chunk.content)
        if normalized in seen:
            continue
        # Skip near-duplicates (first 100 chars match)
        prefix = normalized[:100]
        if any(prefix == s[:100] for s in seen if len(s) >= 100):
            continue
        seen.add(normalized)
        result.append(chunk)

    logger.info(
        "Context compression: %.1fms (%d → %d)",
        (time.perf_counter() - t0) * 1000,
        len(chunks),
        len(result),
    )
    return result
