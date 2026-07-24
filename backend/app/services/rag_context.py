"""Result of RAG context resolution for chat."""

from dataclasses import dataclass, field
from uuid import UUID

from app.providers.types import RetrievedChunk


@dataclass(frozen=True)
class RagContextResult:
    chunks: list[RetrievedChunk]
    has_chunks: bool
    retrieval_degraded: bool = False
    active_document_id: UUID | None = None
    document_filter_ids: list[UUID] | None = None
    chunk_ids: list[str] = field(default_factory=list)
