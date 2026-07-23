from abc import ABC, abstractmethod
from uuid import UUID

from app.providers.types import (
    ChunkPayload,
    EmbeddingBatch,
    ParsedDocument,
    RetrievalContext,
    RetrievedChunk,
    TextChunk,
)


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_query(self, text: str) -> tuple[list[float], dict[int, float] | None]:
        """Return dense + optional sparse embedding for a query."""

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> EmbeddingBatch:
        """Batch-embed document chunks for indexing."""


class VectorStore(ABC):
    @abstractmethod
    async def ensure_collection(self) -> None:
        """Create collection if it does not exist."""

    @abstractmethod
    async def upsert(self, chunks: list[ChunkPayload]) -> None:
        """Upsert chunk vectors with metadata."""

    @abstractmethod
    async def search(
        self,
        project_id: UUID,
        dense_vector: list[float],
        sparse_vector: dict[int, float] | None,
        limit: int,
        document_ids: list[UUID] | None = None,
    ) -> list[RetrievedChunk]:
        """Hybrid search with metadata filtering."""

    @abstractmethod
    async def delete_document(self, document_id: UUID) -> None:
        """Remove all vectors for a document."""

    @abstractmethod
    async def delete_project(self, project_id: UUID) -> None:
        """Remove all vectors for a project."""


class DocumentParser(ABC):
    @abstractmethod
    async def parse(self, file_path: str, mime_type: str) -> ParsedDocument:
        """Extract text from a stored file."""


class Chunker(ABC):
    @abstractmethod
    async def chunk(self, text: str, filename: str) -> list[TextChunk]:
        """Split text into semantic chunks."""


class QueryRewriter(ABC):
    @abstractmethod
    async def rewrite(self, query: str, history: list[dict[str, str]]) -> str:
        """Rewrite a follow-up into a standalone retrieval query."""


class Reranker(ABC):
    @abstractmethod
    async def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        """Cross-encoder reranking."""


class Retriever(ABC):
    @abstractmethod
    async def retrieve(
        self,
        project_id: UUID,
        query: str,
        history: list[dict[str, str]],
        document_ids: list[UUID] | None = None,
    ) -> RetrievalContext:
        """Full retrieval pipeline entry point."""
