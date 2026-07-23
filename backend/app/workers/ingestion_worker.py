from uuid import UUID

from arq.connections import RedisSettings

from app.config import settings
from app.services.ingestion_service import IngestionService

async def process_document(ctx, document_id: str) -> None:
    """Arq worker task: ingest a document through the full RAG pipeline."""
    service = IngestionService()
    await service.ingest(UUID(document_id))


class WorkerSettings:
    functions = [process_document]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    job_timeout = 600
    retry_jobs = True
    max_tries = settings.ingestion_max_retries + 1
