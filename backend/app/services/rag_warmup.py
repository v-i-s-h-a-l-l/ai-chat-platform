"""Preload RAG models so the first chat query after upload stays fast."""

import logging
import time
from uuid import uuid4

from app.config import settings
from app.providers.types import RetrievedChunk

logger = logging.getLogger(__name__)

_warmed = False
_reranker_warmed = False


def _dummy_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        project_id=uuid4(),
        filename="warmup.txt",
        content="warmup context for retrieval model initialization",
        chunk_index=0,
        page_number=None,
        section_heading=None,
        score=1.0,
        source="document",
    )


async def warmup_reranker() -> None:
    """Load the cross-encoder reranker — skipped when RERANK_ENABLED=false."""
    global _reranker_warmed
    if not settings.rag_enabled or not settings.rerank_enabled or _reranker_warmed:
        return

    from app.providers.impl.bge_reranker import get_reranker

    t0 = time.perf_counter()
    chunk = _dummy_chunk()
    await get_reranker().rerank("warmup query", [chunk, chunk], top_k=1)
    _reranker_warmed = True
    logger.info("Reranker warmed up in %.0fms", (time.perf_counter() - t0) * 1000)


async def warmup_rag_models() -> None:
    """Preload local embedding/reranker models when not using Hugging Face API."""
    global _warmed
    if not settings.rag_enabled or _warmed:
        return

    from app.providers.impl.embedding_factory import get_embedding_provider

    t0 = time.perf_counter()
    try:
        if settings.embedding_provider.lower() == "local":
            await get_embedding_provider().embed_query("warmup")
        await warmup_reranker()
        _warmed = True
        logger.info("RAG warmup finished in %.0fms", (time.perf_counter() - t0) * 1000)
    except Exception:
        logger.exception("RAG warmup failed")
