import logging
import time
from uuid import UUID

from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.database import SessionLocal
from app.providers.impl.embedding_factory import get_embedding_provider
from app.providers.impl.bge_reranker import get_reranker
from app.providers.impl.hybrid_retriever import HybridRetriever
from app.providers.impl.llm_query_rewriter import LlmQueryRewriter
from app.providers.impl.qdrant_store import get_vector_store
from app.models.chat_message import ChatMessage
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.services.document_context_resolver import resolve_target_documents
from app.services.llm_provider import LLMProvider
from app.services.rag_context import RagContextResult

logger = logging.getLogger(__name__)


def _build_retriever(llm: LLMProvider) -> HybridRetriever:
    """Build retriever with request-scoped LLM for query rewriting."""
    return HybridRetriever(
        embedder=get_embedding_provider(),
        vector_store=get_vector_store(),
        reranker=get_reranker(),
        query_rewriter=LlmQueryRewriter(llm),
    )


def _history_to_dicts(history: list[ChatMessage]) -> list[dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in history]


def _resolve_document_filter(
    project_id: UUID, query: str
) -> tuple[list[UUID] | None, UUID | None]:
    """O(1) conversation-state lookup + heuristic resolve — no LLM/embed."""
    db = SessionLocal()
    try:
        active_id = ProjectRepository.get_active_document_id(db, project_id)
        resolution = resolve_target_documents(
            db, project_id, query, active_document_id=active_id
        )
        if (
            resolution.reason == "explicit_reference"
            and resolution.document_ids
            and len(resolution.document_ids) == 1
        ):
            ProjectRepository.set_active_document(db, project_id, resolution.document_ids[0])
        elif resolution.reason == "contextual_latest" and resolution.active_document_id:
            ProjectRepository.set_active_document(
                db, project_id, resolution.active_document_id
            )
        return resolution.document_ids, active_id
    finally:
        db.close()


async def resolve_rag_context(
    project_id: UUID,
    query: str,
    history: list[ChatMessage],
    llm: LLMProvider,
) -> RagContextResult:
    """Retrieve document context for a chat query."""
    if not settings.rag_enabled:
        logger.info("RAG disabled — skipping retrieval project=%s", project_id)
        return RagContextResult(chunks=[], has_chunks=False)

    t0 = time.perf_counter()
    try:
        document_ids, active_document_id = await run_in_threadpool(
            _resolve_document_filter, project_id, query
        )
        logger.info(
            "RAG resolve: project=%s active_document=%s filter=%s query=%r",
            project_id,
            active_document_id,
            [str(d) for d in document_ids] if document_ids else "all",
            query[:120],
        )

        retriever = _build_retriever(llm)
        context = await retriever.retrieve(
            project_id=project_id,
            query=query,
            history=_history_to_dicts(history),
            document_ids=document_ids,
        )
        chunk_ids = [str(c.chunk_id) for c in context.chunks]
        context_chars = sum(len(c.content) for c in context.chunks)

        logger.info(
            "RAG retrieval: %.0fms project=%s active=%s chunks=%d chunk_ids=%s "
            "context_chars=%d type=%s filter=%s",
            (time.perf_counter() - t0) * 1000,
            project_id,
            active_document_id,
            len(context.chunks),
            chunk_ids[:5],
            context_chars,
            context.query_type.value,
            [str(d) for d in document_ids] if document_ids else "all",
        )

        if not context.chunks:
            has_ready = await run_in_threadpool(
                DocumentRepository.has_ready_documents, project_id
            )
            if has_ready:
                logger.warning(
                    "RAG retrieval returned 0 chunks but project has Ready documents "
                    "(project=%s active=%s filter=%s)",
                    project_id,
                    active_document_id,
                    document_ids,
                )

        return RagContextResult(
            chunks=context.chunks,
            has_chunks=len(context.chunks) > 0,
            active_document_id=active_document_id,
            document_filter_ids=document_ids,
            chunk_ids=chunk_ids,
        )
    except Exception:
        logger.exception("RAG retrieval failed — continuing without document context")
        has_ready = await run_in_threadpool(
            DocumentRepository.has_ready_documents, project_id
        )
        return RagContextResult(
            chunks=[],
            has_chunks=False,
            retrieval_degraded=has_ready,
        )
