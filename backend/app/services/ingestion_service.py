import logging
import time
from uuid import UUID, uuid4

from app.config import settings
from app.database import SessionLocal
from app.models.document import Document
from app.providers.impl.bge_embedding import get_embedding_provider
from app.providers.impl.document_parser import LlamaDocumentParser
from app.providers.impl.qdrant_store import get_vector_store
from app.providers.impl.semantic_chunker import SemanticChunker
from app.providers.types import ChunkPayload, DocumentStatus
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)


class IngestionService:
    """Background ingestion pipeline: extract → clean → chunk → embed → index."""

    def __init__(self) -> None:
        self._parser = LlamaDocumentParser()
        self._chunker = SemanticChunker()
        self._embedder = get_embedding_provider()
        self._vector_store = get_vector_store()

    async def ingest(self, document_id: UUID) -> None:
        t_total = time.perf_counter()
        db = SessionLocal()
        try:
            doc = db.query(Document).filter_by(id=document_id).first()
            if doc is None:
                logger.error("Document not found: %s", document_id)
                return

            logger.info("Ingestion started: %s (%s)", doc.filename, document_id)

            t0 = time.perf_counter()
            parsed = await self._parser.parse(doc.storage_path, doc.mime_type)
            if not parsed.full_text.strip():
                raise ValueError("No extractable text in document")
            extract_ms = (time.perf_counter() - t0) * 1000
            logger.info("Extraction: %.0fms", extract_ms)

            DocumentChunkRepository.delete_by_document(db, document_id)
            await self._vector_store.delete_document(document_id)

            t0 = time.perf_counter()
            text_chunks = await self._chunker.chunk(parsed.full_text, doc.filename)
            chunk_ms = (time.perf_counter() - t0) * 1000
            logger.info("Chunking: %.0fms (%d chunks)", chunk_ms, len(text_chunks))

            if not text_chunks:
                raise ValueError("Chunking produced no chunks")

            t0 = time.perf_counter()
            texts = [c.content for c in text_chunks]
            embeddings = await self._embedder.embed_documents(texts)
            embed_ms = (time.perf_counter() - t0) * 1000
            logger.info("Embedding: %.0fms", embed_ms)

            payloads: list[ChunkPayload] = []
            chunk_records: list[dict] = []
            for i, tc in enumerate(text_chunks):
                chunk_id = uuid4()
                payloads.append(
                    ChunkPayload(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        project_id=doc.project_id,
                        filename=doc.filename,
                        chunk_index=tc.chunk_index,
                        content=tc.content,
                        page_number=tc.page_number,
                        section_heading=tc.section_heading,
                        dense_vector=embeddings.dense[i],
                        sparse_vector=embeddings.sparse[i],
                    )
                )
                chunk_records.append(
                    {
                        "id": chunk_id,
                        "document_id": document_id,
                        "project_id": doc.project_id,
                        "chunk_index": tc.chunk_index,
                        "content": tc.content,
                        "page_number": tc.page_number,
                        "section_heading": tc.section_heading,
                        "qdrant_point_id": str(chunk_id),
                        "token_count": len(tc.content.split()),
                    }
                )

            t0 = time.perf_counter()
            await self._vector_store.upsert(payloads)
            qdrant_ms = (time.perf_counter() - t0) * 1000
            logger.info("Qdrant upsert: %.0fms", qdrant_ms)

            DocumentChunkRepository.create_batch(db, chunk_records)
            DocumentRepository.update_status(
                db, document_id, DocumentStatus.READY.value, chunk_count=len(text_chunks)
            )

            total_ms = (time.perf_counter() - t_total) * 1000
            logger.info(
                "Ingestion complete: %s — %d chunks in %.0fms (extract=%.0f chunk=%.0f embed=%.0f qdrant=%.0f)",
                doc.filename,
                len(text_chunks),
                total_ms,
                extract_ms,
                chunk_ms,
                embed_ms,
                qdrant_ms,
            )

        except Exception as exc:
            logger.exception("Ingestion failed for document %s", document_id)
            retry = DocumentRepository.increment_retry(db, document_id)
            status = (
                DocumentStatus.FAILED.value
                if retry >= settings.ingestion_max_retries
                else DocumentStatus.PROCESSING.value
            )
            DocumentRepository.update_status(db, document_id, status, error_message=str(exc)[:2000])
            if retry < settings.ingestion_max_retries:
                raise  # arq will retry
        finally:
            db.close()
