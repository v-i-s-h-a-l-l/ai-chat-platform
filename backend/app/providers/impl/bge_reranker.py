import logging
import time
from functools import lru_cache

from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.providers.base import Reranker
from app.providers.types import RetrievedChunk

logger = logging.getLogger(__name__)

_model = None


def _get_reranker():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder

        logger.info("Loading reranker model: %s", settings.reranker_model)
        _model = CrossEncoder(settings.reranker_model, trust_remote_code=True)
        logger.info("Reranker model loaded")
    return _model


class PassthroughReranker(Reranker):
    """Skip cross-encoder reranking (used when RERANK_ENABLED=false)."""

    async def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        return chunks[:top_k]


class BgeReranker(Reranker):
    """Singleton BGE cross-encoder reranker."""

    async def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []
        if len(chunks) <= top_k:
            return chunks

        t0 = time.perf_counter()

        def _rerank() -> list[RetrievedChunk]:
            model = _get_reranker()
            pairs = [[query, c.content] for c in chunks]
            scores = model.predict(pairs)
            scored = sorted(zip(chunks, scores, strict=True), key=lambda x: x[1], reverse=True)
            return [
                RetrievedChunk(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    project_id=c.project_id,
                    filename=c.filename,
                    content=c.content,
                    chunk_index=c.chunk_index,
                    page_number=c.page_number,
                    section_heading=c.section_heading,
                    score=float(score),
                    source=c.source,
                )
                for c, score in scored[:top_k]
            ]

        result = await run_in_threadpool(_rerank)
        logger.info("Reranking: %.1fms (%d → %d)", (time.perf_counter() - t0) * 1000, len(chunks), len(result))
        return result


@lru_cache(maxsize=1)
def get_reranker() -> Reranker:
    if not settings.rerank_enabled:
        return PassthroughReranker()
    return BgeReranker()
