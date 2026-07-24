import logging
import time
from uuid import UUID

from app.config import settings
from app.models.chat_message import ChatMessage
from app.providers.impl.bge_embedding import get_embedding_provider
from app.providers.impl.bge_reranker import get_reranker
from app.providers.impl.hybrid_retriever import HybridRetriever
from app.providers.impl.llm_query_rewriter import LlmQueryRewriter
from app.providers.impl.qdrant_store import get_vector_store
from app.providers.types import RetrievedChunk
from app.services.llm_provider import LLMProvider

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


async def resolve_rag_context(
    project_id: UUID,
    query: str,
    history: list[ChatMessage],
    llm: LLMProvider,
) -> tuple[list[RetrievedChunk], bool]:
    """Retrieve document context for a chat query. Returns (chunks, documents_used)."""
    if not settings.rag_enabled:
        return [], False

    t0 = time.perf_counter()
    try:
        retriever = _build_retriever(llm)
        context = await retriever.retrieve(
            project_id=project_id,
            query=query,
            history=_history_to_dicts(history),
        )
        used = len(context.chunks) > 0
        if used:
            logger.info(
                "RAG retrieval: %.0fms, %d chunks, type=%s",
                (time.perf_counter() - t0) * 1000,
                len(context.chunks),
                context.query_type.value,
            )
        return context.chunks, used
    except Exception:
        logger.exception("RAG retrieval failed — continuing without document context")
        return [], False
