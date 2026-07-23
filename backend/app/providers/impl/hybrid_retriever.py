import logging
import time
from uuid import UUID

from app.config import settings
from app.providers.base import EmbeddingProvider, QueryRewriter, Reranker, Retriever, VectorStore
from app.providers.types import QueryType, RetrievalContext
from app.repositories.document_repository import DocumentRepository
from app.services.context_compressor import compress_context
from app.services.mmr import apply_mmr
from app.services.query_classifier import classify_query

logger = logging.getLogger(__name__)


class HybridRetriever(Retriever):
    """Full retrieval pipeline: rewrite → classify → embed → hybrid → MMR → rerank → compress."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        vector_store: VectorStore,
        reranker: Reranker,
        query_rewriter: QueryRewriter,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._reranker = reranker
        self._query_rewriter = query_rewriter

    async def retrieve(
        self,
        project_id: UUID,
        query: str,
        history: list[dict[str, str]],
        document_ids: list[UUID] | None = None,
    ) -> RetrievalContext:
        timings: dict[str, float] = {}
        t_total = time.perf_counter()

        has_docs = DocumentRepository.has_ready_documents(project_id)
        query_type = classify_query(query, has_docs)
        timings["classification"] = (time.perf_counter() - t_total) * 1000

        if query_type == QueryType.GENERAL or not has_docs:
            return RetrievalContext(
                query_type=query_type,
                rewritten_query=query,
                chunks=[],
                timings_ms=timings,
            )

        t0 = time.perf_counter()
        rewritten = await self._query_rewriter.rewrite(query, history)
        timings["rewrite"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        dense, sparse = await self._embedder.embed_query(rewritten)
        timings["embedding"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        candidates = await self._vector_store.search(
            project_id=project_id,
            dense_vector=dense,
            sparse_vector=sparse,
            limit=settings.rag_top_k,
            document_ids=document_ids,
        )
        timings["qdrant"] = (time.perf_counter() - t0) * 1000

        if not candidates:
            timings["total"] = (time.perf_counter() - t_total) * 1000
            return RetrievalContext(
                query_type=query_type,
                rewritten_query=rewritten,
                chunks=[],
                timings_ms=timings,
            )

        t0 = time.perf_counter()
        mmr_results = apply_mmr(candidates, top_k=settings.rag_top_k)
        timings["mmr"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        reranked = await self._reranker.rerank(rewritten, mmr_results, settings.rag_rerank_top_k)
        timings["rerank"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        compressed = compress_context(reranked)
        timings["compression"] = (time.perf_counter() - t0) * 1000
        timings["total"] = (time.perf_counter() - t_total) * 1000

        logger.info(
            "Retrieval pipeline: total=%.0fms embed=%.0fms qdrant=%.0fms rerank=%.0fms chunks=%d",
            timings["total"],
            timings.get("embedding", 0),
            timings.get("qdrant", 0),
            timings.get("rerank", 0),
            len(compressed),
        )

        return RetrievalContext(
            query_type=query_type,
            rewritten_query=rewritten,
            chunks=compressed,
            timings_ms=timings,
        )
