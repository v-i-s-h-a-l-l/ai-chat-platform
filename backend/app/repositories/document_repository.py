from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document
from app.providers.types import DocumentStatus


class DocumentRepository:
    @staticmethod
    def create(
        db: Session,
        project_id: UUID,
        filename: str,
        storage_path: str,
        mime_type: str,
        file_size: int,
    ) -> Document:
        doc = Document(
            project_id=project_id,
            filename=filename,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size=file_size,
            status=DocumentStatus.PROCESSING.value,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def get_by_id(db: Session, document_id: UUID, project_id: UUID) -> Document | None:
        return (
            db.query(Document)
            .filter(Document.id == document_id, Document.project_id == project_id)
            .first()
        )

    @staticmethod
    def list_by_project(db: Session, project_id: UUID) -> list[Document]:
        return (
            db.query(Document)
            .filter(Document.project_id == project_id)
            .order_by(Document.created_at.desc())
            .all()
        )

    @staticmethod
    def update_status(
        db: Session,
        document_id: UUID,
        status: str,
        error_message: str | None = None,
        chunk_count: int | None = None,
    ) -> None:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            return
        doc.status = status
        if error_message is not None:
            doc.error_message = error_message
        elif status == DocumentStatus.READY.value:
            doc.error_message = None
        if chunk_count is not None:
            doc.chunk_count = chunk_count
        db.commit()

    @staticmethod
    def increment_retry(db: Session, document_id: UUID) -> int:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            return 0
        doc.retry_count += 1
        db.commit()
        return doc.retry_count

    @staticmethod
    def touch(db: Session, document_id: UUID) -> None:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            return
        doc.updated_at = datetime.now(timezone.utc)
        db.commit()

    @staticmethod
    def list_stale_processing(
        db: Session, project_id: UUID, *, older_than_minutes: int
    ) -> list[Document]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
        return (
            db.query(Document)
            .filter(
                Document.project_id == project_id,
                Document.status == DocumentStatus.PROCESSING.value,
                Document.updated_at <= cutoff,
            )
            .all()
        )

    @staticmethod
    def delete(db: Session, document: Document) -> None:
        db.delete(document)
        db.commit()

    @staticmethod
    def has_ready_documents(project_id: UUID) -> bool:
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            count = (
                db.query(Document)
                .filter(
                    Document.project_id == project_id,
                    Document.status == DocumentStatus.READY.value,
                )
                .count()
            )
            return count > 0
        finally:
            db.close()
