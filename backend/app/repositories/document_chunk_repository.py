from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk


class DocumentChunkRepository:
    @staticmethod
    def create_batch(
        db: Session,
        chunks: list[dict],
    ) -> list[DocumentChunk]:
        records = []
        for data in chunks:
            record = DocumentChunk(
                id=data.get("id", uuid4()),
                document_id=data["document_id"],
                project_id=data["project_id"],
                chunk_index=data["chunk_index"],
                content=data["content"],
                page_number=data.get("page_number"),
                section_heading=data.get("section_heading"),
                qdrant_point_id=data["qdrant_point_id"],
                token_count=data.get("token_count", 0),
            )
            db.add(record)
            records.append(record)
        db.commit()
        for r in records:
            db.refresh(r)
        return records

    @staticmethod
    def delete_by_document(db: Session, document_id: UUID) -> None:
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        db.commit()

    @staticmethod
    def list_by_document(db: Session, document_id: UUID) -> list[DocumentChunk]:
        return (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
