"""End-to-end RAG pipeline behavior tests (retrieval routing + prompt assembly)."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.chat_message import ChatMessage
from app.providers.types import QueryType, RetrievedChunk
from app.services.message_builder import build_routed_llm_messages
from app.services.query_classifier import classify_query, is_document_intent_query
from app.services.response_router import DocumentCoverage, resolve_response_route


def _chunk(content: str = "Transformer architecture with multi-head attention.", score: float = 0.9):
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        project_id=uuid4(),
        filename="attention-paper.pdf",
        content=content,
        chunk_index=0,
        page_number=1,
        section_heading="Abstract",
        score=score,
    )


class FakeProvider:
    async def fast_complete(self, messages, max_tokens=8):
        return "NONE"


@pytest.mark.parametrize(
    "query",
    [
        "What is this document about?",
        "Summarize the uploaded PDF.",
        "What are the key topics?",
        "Explain page 3.",
        "List the important formulas.",
    ],
)
def test_document_intent_queries_are_classified(query: str):
    assert is_document_intent_query(query) is True
    assert classify_query(query, has_documents=True) == QueryType.DOCUMENT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "What is this document about?",
        "Summarize the uploaded PDF.",
        "What are the key topics?",
    ],
)
async def test_document_intent_with_chunks_always_uses_documents(query: str):
    chunks = [_chunk()]
    route = await resolve_response_route(FakeProvider(), query, chunks)

    assert route.documents_used is True
    assert route.doc_chunks == chunks
    assert route.web_search_used is False
    assert route.general_knowledge_used is False
    assert route.coverage == DocumentCoverage.FULL


@pytest.mark.asyncio
async def test_document_intent_without_chunks_skips_general_knowledge():
    route = await resolve_response_route(FakeProvider(), "Summarize this file.", [])

    assert route.documents_used is False
    assert route.general_knowledge_used is False
    assert route.web_search_used is False


def test_routed_prompt_includes_context_section():
    chunks = [_chunk()]
    from app.services.response_router import ResponseRoute

    response_route = ResponseRoute(
        coverage=DocumentCoverage.FULL,
        doc_chunks=chunks,
        search_results=[],
        documents_used=True,
        web_search_used=False,
        general_knowledge_used=False,
    )
    messages = build_routed_llm_messages(
        "You are an AI assistant.",
        [],
        "What is this document about?",
        response_route,
    )

    system = messages[0]["content"]
    user_turn = messages[1]["content"]

    assert "Context:" in user_turn
    assert "attention-paper.pdf" in user_turn
    assert "Never say you cannot access uploaded documents" in system
    assert "ROUTING" not in system  # sanity — routing constants are content not names


@pytest.mark.asyncio
@patch("app.providers.impl.hybrid_retriever.run_in_threadpool", new_callable=AsyncMock)
async def test_retriever_does_not_skip_document_about_query(mock_threadpool):
    from app.providers.impl.hybrid_retriever import HybridRetriever

    mock_threadpool.return_value = True
    embedder = AsyncMock()
    embedder.embed_query.return_value = ([0.1], {"indices": [1], "values": [0.5]})
    vector_store = AsyncMock()
    vector_store.search.return_value = [_chunk("Overview of the paper.", score=0.88)]
    reranker = AsyncMock()
    reranker.rerank.side_effect = lambda q, c, k: c[:k]
    rewriter = AsyncMock()
    rewriter.rewrite.return_value = "overview"

    retriever = HybridRetriever(embedder, vector_store, reranker, rewriter)
    result = await retriever.retrieve(uuid4(), "What is this document about?", [])

    assert len(result.chunks) > 0
    vector_store.search.assert_awaited()
