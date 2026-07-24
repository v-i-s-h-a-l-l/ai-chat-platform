"""Enqueue document ingestion jobs on the Arq worker.

Production default: fail closed when Redis is unavailable so heavy embedding
work never runs inside the API process.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings
from app.services.ingestion_errors import IngestionQueueUnavailableError

logger = logging.getLogger(__name__)

_pool = None
_pool_lock = asyncio.Lock()


async def _get_pool():
    global _pool
    if _pool is not None:
        return _pool
    async with _pool_lock:
        if _pool is None:
            _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool


async def enqueue_document_ingestion(document_id: UUID) -> None:
    """Schedule ingestion on the background worker (non-blocking for HTTP handlers)."""
    from app.observability import metrics
    from app.services.ingestion_service import IngestionService

    try:
        pool = await _get_pool()
        job = await pool.enqueue_job("process_document", str(document_id))
        metrics.INGESTION_ENQUEUED.inc()
        logger.info("Enqueued ingestion job %s for document %s", job.job_id, document_id)
        return
    except Exception as exc:
        metrics.INGESTION_ENQUEUE_FAILURES.inc()
        if not settings.ingestion_inline_fallback:
            logger.error(
                "Failed to enqueue ingestion for %s (inline fallback disabled): %s",
                document_id,
                exc,
            )
            raise IngestionQueueUnavailableError(str(document_id), cause=exc) from exc

        logger.warning(
            "Failed to enqueue ingestion for %s, running inline fallback (dev only): %s",
            document_id,
            exc,
        )

        async def _run() -> None:
            try:
                metrics.INGESTION_INLINE_FALLBACK.inc()
                await IngestionService().ingest(document_id)
            except Exception:
                logger.exception("Background ingestion failed for %s", document_id)

        asyncio.create_task(_run())
