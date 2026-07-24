"""Ingestion service tests — error truncation and Qdrant failure handling."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.providers.types import DocumentStatus
from app.services.ingestion_service import IngestionService
from app.utils.errors import CLIENT_ERROR_MAX_LEN


@pytest.fixture
def service():
    with patch("app.services.ingestion_service.LlamaDocumentParser"):
        with patch("app.services.ingestion_service.SemanticChunker"):
            with patch("app.services.ingestion_service.get_embedding_provider"):
                with patch("app.services.ingestion_service.get_vector_store"):
                    return IngestionService()


@pytest.mark.asyncio
async def test_ingestion_truncates_error_message(service):
    document_id = uuid4()
    long_error = "x" * 500
    doc = MagicMock(
        id=document_id,
        filename="notes.txt",
        storage_path="/tmp/notes.txt",
        mime_type="text/plain",
        project_id=uuid4(),
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value = doc

    with patch("app.services.ingestion_service.SessionLocal", return_value=mock_db):
        service._parser.parse = AsyncMock(side_effect=ValueError(long_error))
        with patch(
            "app.services.ingestion_service.DocumentRepository.increment_retry",
            return_value=3,
        ):
            with patch(
                "app.services.ingestion_service.DocumentRepository.update_status"
            ) as mock_update:
                await service.ingest(document_id)

    mock_update.assert_called_once()
    error_message = mock_update.call_args.kwargs["error_message"]
    assert len(error_message) <= CLIENT_ERROR_MAX_LEN
    assert mock_update.call_args[0][2] == DocumentStatus.FAILED.value


@pytest.mark.asyncio
async def test_ingestion_fails_immediately_for_scanned_pdf(service):
    document_id = uuid4()
    doc = MagicMock(
        id=document_id,
        filename="scan.pdf",
        storage_path="/tmp/scan.pdf",
        mime_type="application/pdf",
        project_id=uuid4(),
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value = doc

    with patch("app.services.ingestion_service.SessionLocal", return_value=mock_db):
        service._parser.parse = AsyncMock(
            side_effect=ValueError(
                "This PDF looks like a scan or image — no readable text was found."
            )
        )
        with patch(
            "app.services.ingestion_service.DocumentRepository.increment_retry",
            return_value=1,
        ):
            with patch(
                "app.services.ingestion_service.DocumentRepository.update_status"
            ) as mock_update:
                await service.ingest(document_id)

    assert mock_update.call_args[0][2] == DocumentStatus.FAILED.value
    assert "scan or image" in mock_update.call_args.kwargs["error_message"]


@pytest.mark.asyncio
async def test_ingestion_marks_ready_only_after_qdrant_upsert(service):
    document_id = uuid4()
    project_id = uuid4()
    doc = MagicMock(
        id=document_id,
        filename="notes.txt",
        storage_path="/tmp/notes.txt",
        mime_type="text/plain",
        project_id=project_id,
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value = doc

    parsed = MagicMock(full_text="Hello world")
    text_chunk = MagicMock(content="Hello world", chunk_index=0, page_number=1, section_heading=None)
    embeddings = MagicMock(dense=[[0.1, 0.2]], sparse=[None])

    service._parser.parse = AsyncMock(return_value=parsed)
    service._chunker.chunk = AsyncMock(return_value=[text_chunk])
    service._embedder.embed_documents = AsyncMock(return_value=embeddings)
    service._vector_store.delete_document = AsyncMock()
    service._vector_store.upsert = AsyncMock()

    call_order: list[str] = []

    async def track_upsert(*_args, **_kwargs):
        call_order.append("upsert")

    service._vector_store.upsert = AsyncMock(side_effect=track_upsert)

    def track_ready(*_args, **_kwargs):
        call_order.append("ready")

    with patch("app.services.ingestion_service.SessionLocal", return_value=mock_db):
        with patch(
            "app.services.ingestion_service.DocumentChunkRepository.delete_by_document"
        ):
            with patch(
                "app.services.ingestion_service.DocumentChunkRepository.create_batch"
            ):
                with patch(
                    "app.services.ingestion_service.DocumentRepository.update_status",
                    side_effect=track_ready,
                ):
                    with patch(
                        "app.repositories.project_repository.ProjectRepository.set_active_document"
                    ):
                        await service.ingest(document_id)

    assert call_order == ["upsert", "ready"]
