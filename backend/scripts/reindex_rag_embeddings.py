"""Drop Qdrant vectors and re-queue all ready documents after an embedding model change.

Usage (from backend/):
    python -m scripts.reindex_rag_embeddings
"""

import asyncio
import logging

from app.database import SessionLocal
from app.models.document import Document
from app.providers.impl.qdrant_store import get_vector_store
from app.providers.types import DocumentStatus
from app.services.ingestion_queue import enqueue_document_ingestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    store = get_vector_store()
    await store.recreate_collection()

    db = SessionLocal()
    try:
        docs = (
            db.query(Document)
            .filter(Document.status == DocumentStatus.READY.value)
            .order_by(Document.created_at.asc())
            .all()
        )
        for doc in docs:
            doc.status = DocumentStatus.PROCESSING.value
            doc.retry_count = 0
            doc.error_message = None
        db.commit()

        for doc in docs:
            await enqueue_document_ingestion(doc.id)

        logger.info("Re-queued %d document(s) for ingestion", len(docs))
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
