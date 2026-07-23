import logging
import re
import time

from starlette.concurrency import run_in_threadpool

from app.providers.base import Chunker
from app.providers.types import TextChunk

logger = logging.getLogger(__name__)

HEADING_PATTERN = re.compile(r"^(#{1,6}\s+.+|[A-Z][A-Za-z0-9\s\-:,]{2,60}$)", re.MULTILINE)
MIN_CHUNK_CHARS = 80
TARGET_CHUNK_CHARS = 600
MAX_CHUNK_CHARS = 1200


def _split_into_sections(text: str) -> list[tuple[str | None, str]]:
    """Split on markdown-style headings, preserving section boundaries."""
    sections: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        if HEADING_PATTERN.match(line.strip()) and len(line.strip()) < 80:
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append((current_heading, body))
            current_heading = line.strip().lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_heading, body))

    if not sections:
        return [(None, text)]
    return sections


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paragraphs if paragraphs else [text]


def _merge_to_target(paragraphs: list[str]) -> list[str]:
    """Merge paragraphs into semantic chunks without splitting sentences mid-way."""
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(para) > MAX_CHUNK_CHARS:
            if current:
                chunks.append(current.strip())
                current = ""
            sentences = re.split(r"(?<=[.!?])\s+", para)
            buf = ""
            for sent in sentences:
                if len(buf) + len(sent) + 1 > TARGET_CHUNK_CHARS and buf:
                    chunks.append(buf.strip())
                    buf = sent
                else:
                    buf = f"{buf} {sent}".strip() if buf else sent
            if buf:
                chunks.append(buf.strip())
            continue

        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) > TARGET_CHUNK_CHARS and current:
            chunks.append(current.strip())
            current = para
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if len(c) >= MIN_CHUNK_CHARS or not chunks]


class SemanticChunker(Chunker):
    """Semantic chunking: preserve headings, paragraphs, and section boundaries."""

    async def chunk(self, text: str, filename: str) -> list[TextChunk]:
        t0 = time.perf_counter()

        def _chunk() -> list[TextChunk]:
            sections = _split_into_sections(text)
            result: list[TextChunk] = []
            idx = 0

            for heading, body in sections:
                paragraphs = _split_paragraphs(body)
                merged = _merge_to_target(paragraphs)
                for chunk_text in merged:
                    result.append(
                        TextChunk(
                            content=chunk_text,
                            chunk_index=idx,
                            section_heading=heading,
                        )
                    )
                    idx += 1

            if not result and text.strip():
                result.append(TextChunk(content=text.strip(), chunk_index=0))

            return result

        chunks = await run_in_threadpool(_chunk)
        logger.info(
            "Semantic chunking (%s): %d chunks in %.1fms",
            filename,
            len(chunks),
            (time.perf_counter() - t0) * 1000,
        )
        return chunks
