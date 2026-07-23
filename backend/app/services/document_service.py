import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
import app.guardrails as guardrails
from app.models.document import Document
from app.providers.impl.qdrant_store import get_vector_store
from app.providers.types import DocumentStatus
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.services.ingestion_service import IngestionService
from app.services.project_service import ProjectService
from app.utils.file_storage import FileStorage

logger = logging.getLogger(__name__)

ALLOWED_MIMES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class DocumentService:
    @staticmethod
    def list_documents(db: Session, project_id: UUID, user_id: UUID) -> list[Document]:
        ProjectService.get_project(db, project_id, user_id)
        return DocumentRepository.list_by_project(db, project_id)

    @staticmethod
    async def upload_document(
        db: Session,
        project_id: UUID,
        user_id: UUID,
        filename: str,
        mime_type: str,
        data: bytes,
    ) -> Document:
        ProjectService.get_project(db, project_id, user_id)

        if mime_type not in ALLOWED_MIMES:
            raise ValueError(f"Unsupported file type: {mime_type}")

        max_bytes = settings.rag_max_upload_mb * 1024 * 1024
        if len(data) > max_bytes:
            raise ValueError(f"File exceeds maximum size of {settings.rag_max_upload_mb} MB")

        # Guardrails: check for PII in upload
        if settings.guardrails_enabled:
            guardrails.check_document(filename, data)

        storage = FileStorage()
        doc = DocumentRepository.create(
            db,
            project_id=project_id,
            filename=filename,
            storage_path="",  # placeholder
            mime_type=mime_type,
            file_size=len(data),
        )

        path = await storage.save(project_id, doc.id, filename, data)
        doc.storage_path = path
        db.commit()
        db.refresh(doc)

        await IngestionService().ingest(doc.id)
        db.refresh(doc)
        logger.info("Document uploaded and ingested: %s (status=%s)", doc.id, doc.status)
        return doc

    @staticmethod
    async def delete_document(
        db: Session, project_id: UUID, user_id: UUID, document_id: UUID
    ) -> None:
        ProjectService.get_project(db, project_id, user_id)
        doc = DocumentRepository.get_by_id(db, document_id, project_id)
        if doc is None:
            raise ValueError("Document not found")

        storage = FileStorage()
        await storage.delete(doc.storage_path)
        await get_vector_store().delete_document(document_id)
        DocumentChunkRepository.delete_by_document(db, document_id)
        DocumentRepository.delete(db, doc)

    @staticmethod
    async def reprocess_document(
        db: Session, project_id: UUID, user_id: UUID, document_id: UUID
    ) -> Document:
        ProjectService.get_project(db, project_id, user_id)
        doc = DocumentRepository.get_by_id(db, document_id, project_id)
        if doc is None:
            raise ValueError("Document not found")
        if doc.status == DocumentStatus.READY.value:
            return doc

        await IngestionService().ingest(document_id)
        db.refresh(doc)
        return doc
