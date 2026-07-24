import logging
import time
from uuid import UUID

from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.providers.base import EmbeddingProvider, QueryRewriter, Reranker, Retriever, VectorStore
from app.providers.types import QueryType, RetrievalContext
from app.repositories.document_repository import DocumentRepository
from app.services.context_compressor import compress_context
from app.services.mmr import apply_mmr
from app.services.query_classifier import classify_query, is_document_intent_query
from app.services.routing_heuristics import is_document_access_query

logger = logging.getLogger(__name__)

_DOCUMENT_SEARCH_FALLBACK = (
    "Overview summary main topics key sections and important content of the document"
)
RERANK_SKIP_SCORE = 0.72


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

    async def _search(
        self,
        project_id: UUID,
        search_query: str,
        document_ids: list[UUID] | None,
    ):
        dense, sparse = await self._embedder.embed_query(search_query)
        return await self._vector_store.search(
            project_id=project_id,
            dense_vector=dense,
            sparse_vector=sparse,
            limit=settings.rag_top_k,
            document_ids=document_ids,
        )

    async def retrieve(
        self,
        project_id: UUID,
        query: str,
        history: list[dict[str, str]],
        document_ids: list[UUID] | None = None,
    ) -> RetrievalContext:
        timings: dict[str, float] = {}
        t_total = time.perf_counter()

        has_docs = await run_in_threadpool(DocumentRepository.has_ready_documents, project_id)
        query_type = classify_query(query, has_docs)
        doc_intent = is_document_intent_query(query)
        timings["classification"] = (time.perf_counter() - t_total) * 1000

        if not has_docs:
            logger.info("Retrieval skipped: no Ready documents project=%s", project_id)
            return RetrievalContext(
                query_type=query_type,
                rewritten_query=query,
                chunks=[],
                timings_ms=timings,
            )

        if query_type == QueryType.GENERAL and not doc_intent:
            logger.info("Retrieval skipped: general query project=%s query=%r", project_id, query[:80])
            return RetrievalContext(
                query_type=query_type,
                rewritten_query=query,
                chunks=[],
                timings_ms=timings,
            )

        t0 = time.perf_counter()
        rewritten = await self._query_rewriter.rewrite(query, history)
        timings["rewrite"] = (time.perf_counter() - t0) * 1000

        if is_document_access_query(query) or doc_intent:
            search_query = _DOCUMENT_SEARCH_FALLBACK
        else:
            search_query = rewritten

        t0 = time.perf_counter()
        candidates = await self._search(project_id, search_query, document_ids)
        timings["qdrant"] = (time.perf_counter() - t0) * 1000

        if not candidates and document_ids:
            logger.info(
                "Retrieval: no hits with doc filter %s — retrying all project docs",
                [str(d) for d in document_ids],
            )
            t0 = time.perf_counter()
            candidates = await self._search(project_id, search_query, None)
            timings["qdrant_fallback"] = (time.perf_counter() - t0) * 1000

        if not candidates and doc_intent:
            logger.info("Retrieval: document intent — retrying with broad overview query")
            t0 = time.perf_counter()
            candidates = await self._search(project_id, _DOCUMENT_SEARCH_FALLBACK, document_ids)
            timings["qdrant_broad"] = (time.perf_counter() - t0) * 1000
            if not candidates:
                candidates = await self._search(project_id, _DOCUMENT_SEARCH_FALLBACK, None)

        if not candidates:
            timings["total"] = (time.perf_counter() - t_total) * 1000
            logger.warning(
                "Retrieval: zero Qdrant hits project=%s filter=%s query=%r",
                project_id,
                document_ids,
                query[:80],
            )
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
        top_score = max(candidate.score for candidate in mmr_results)
        if top_score >= RERANK_SKIP_SCORE and len(mmr_results) <= settings.rag_rerank_top_k:
            reranked = mmr_results[: settings.rag_rerank_top_k]
            timings["rerank"] = 0.0
        else:
            reranked = await self._reranker.rerank(search_query, mmr_results, settings.rag_rerank_top_k)
            timings["rerank"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        compressed = compress_context(reranked)
        timings["compression"] = (time.perf_counter() - t0) * 1000
        timings["total"] = (time.perf_counter() - t_total) * 1000

        logger.info(
            "Retrieval pipeline: total=%.0fms qdrant=%.0fms rerank=%.0fms "
            "top_score=%.2f chunks=%d project=%s",
            timings["total"],
            timings.get("qdrant", 0),
            timings.get("rerank", 0),
            top_score,
            len(compressed),
            project_id,
        )

        try:
            from app.observability import metrics

            metrics.RAG_DURATION.observe(timings["total"] / 1000.0)
            metrics.RAG_CHUNKS.observe(len(compressed))
        except Exception:
            pass

        return RetrievalContext(
            query_type=query_type,
            rewritten_query=rewritten,
            chunks=compressed,
            timings_ms=timings,
        )
