import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document
from app.providers.impl.qdrant_store import get_vector_store
from app.providers.types import DocumentStatus
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.services.ingestion_errors import IngestionQueueUnavailableError
from app.services.ingestion_queue import enqueue_document_ingestion
from app.services.project_service import ProjectService
from app.utils.file_storage import FileStorage
from app.utils.mime_validation import ALLOWED_MIMES

logger = logging.getLogger(__name__)


class DocumentService:
    @staticmethod
    async def _recover_stale_processing(db: Session, project_id: UUID) -> None:
        stale = DocumentRepository.list_stale_processing(
            db, project_id, older_than_minutes=settings.ingestion_stale_minutes
        )
        if not stale:
            return

        for doc in stale:
            logger.warning(
                "Re-queuing stale processing document: %s (%s)",
                doc.filename,
                doc.id,
            )
            DocumentRepository.touch(db, doc.id)
            try:
                await enqueue_document_ingestion(doc.id)
            except IngestionQueueUnavailableError:
                logger.error("Cannot re-queue stale document %s — queue unavailable", doc.id)
                DocumentRepository.update_status(
                    db,
                    doc.id,
                    DocumentStatus.FAILED.value,
                    error_message="Ingestion queue unavailable — start Redis and the worker, then reprocess",
                )

    @staticmethod
    async def list_documents_with_recovery(
        db: Session, project_id: UUID, user_id: UUID
    ) -> list[Document]:
        ProjectService.get_project(db, project_id, user_id)
        await DocumentService._recover_stale_processing(db, project_id)
        return DocumentRepository.list_by_project(db, project_id)

    @staticmethod
    async def upload_document(
        db: Session,
        project_id: UUID,
        user_id: UUID,
        filename: str,
        mime_type: str,
        data: bytes,
        *,
        confirmed: bool = False,
    ) -> Document:
        ProjectService.get_project(db, project_id, user_id)

        if mime_type not in ALLOWED_MIMES:
            raise ValueError(f"Unsupported file type: {mime_type}")

        max_bytes = settings.rag_max_upload_mb * 1024 * 1024
        if len(data) > max_bytes:
            raise ValueError(f"File exceeds maximum size of {settings.rag_max_upload_mb} MB")

        if settings.guardrails_enabled:
            from app.services.upload_validation import UploadDecisionService

            await UploadDecisionService().evaluate_and_enforce(
                filename,
                mime_type,
                data,
                confirmed=confirmed,
            )

        storage = FileStorage()
        doc = DocumentRepository.create(
            db,
            project_id=project_id,
            filename=filename,
            storage_path="",
            mime_type=mime_type,
            file_size=len(data),
        )

        path = await storage.save(project_id, doc.id, filename, data)
        doc.storage_path = path
        db.commit()
        db.refresh(doc)

        try:
            await enqueue_document_ingestion(doc.id)
        except IngestionQueueUnavailableError:
            DocumentRepository.update_status(
                db,
                doc.id,
                DocumentStatus.FAILED.value,
                error_message="Ingestion queue unavailable — start Redis and the worker, then reprocess",
            )
            db.refresh(doc)
            raise

        db.refresh(doc)
        logger.info("Document uploaded, ingestion queued: %s (status=%s)", doc.id, doc.status)
        return doc

    @staticmethod
    async def delete_document(
        db: Session, project_id: UUID, user_id: UUID, document_id: UUID
    ) -> None:
        ProjectService.get_project(db, project_id, user_id)
        doc = DocumentRepository.get_by_id(db, document_id, project_id)
        if doc is None:
            raise ValueError("Document not found")

        was_active = ProjectRepository.get_active_document_id(db, project_id) == document_id

        storage = FileStorage()
        await storage.delete(doc.storage_path)
        await get_vector_store().delete_document(document_id)
        DocumentChunkRepository.delete_by_document(db, document_id)
        DocumentRepository.delete(db, doc)

        if was_active:
            latest = DocumentRepository.get_latest_ready(db, project_id)
            ProjectRepository.set_active_document(
                db, project_id, latest.id if latest else None
            )

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

        await enqueue_document_ingestion(document_id)
        db.refresh(doc)
        return doc
