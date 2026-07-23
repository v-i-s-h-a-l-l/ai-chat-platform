"""Shared domain types for the RAG pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class DocumentStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class QueryType(str, Enum):
    GENERAL = "general"
    DOCUMENT = "document"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    pages: list[ParsedPage]
    full_text: str


@dataclass(frozen=True)
class TextChunk:
    content: str
    chunk_index: int
    page_number: int | None = None
    section_heading: str | None = None


@dataclass(frozen=True)
class ChunkPayload:
    """Chunk ready for vector upsert."""

    chunk_id: UUID
    document_id: UUID
    project_id: UUID
    filename: str
    chunk_index: int
    content: str
    page_number: int | None
    section_heading: str | None
    dense_vector: list[float]
    sparse_vector: dict[int, float] | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    project_id: UUID
    filename: str
    content: str
    chunk_index: int
    page_number: int | None
    section_heading: str | None
    score: float
    source: str = "document"


@dataclass
class RetrievalContext:
    query_type: QueryType
    rewritten_query: str
    chunks: list[RetrievedChunk] = field(default_factory=list)
    timings_ms: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EmbeddingBatch:
    dense: list[list[float]]
    sparse: list[dict[int, float] | None]
