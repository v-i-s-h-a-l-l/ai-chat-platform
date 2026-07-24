"""Lightweight response routing after document retrieval.

Determines whether to answer from uploaded documents, general knowledge,
or web search — without modifying the RAG or search orchestrator internals.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

from app.providers.types import RetrievedChunk
from app.services.llm_provider import LLMProvider
from app.services.query_classifier import is_document_intent_query
from app.services.routing_heuristics import heuristic_question_nature, is_document_access_query
from app.services.search_service import SearchResult, SearchService

logger = logging.getLogger(__name__)

MAX_CHUNKS_FOR_ASSESSMENT = 5
MAX_CHUNK_CHARS = 600
HIGH_CONFIDENCE_CHUNK_SCORE = 0.72

COVERAGE_PROMPT = """You are evaluating whether uploaded document excerpts can answer a user question.

Question:
{question}

Document excerpts:
{excerpts}

Can these excerpts answer the question?
Answer ONLY one word:
- FULL — the excerpts fully answer the question
- PARTIAL — the excerpts answer part of the question but important parts are missing
- NONE — the excerpts do not meaningfully answer the question

Answer:"""

NATURE_PROMPT = """Classify this question for information routing.

Questions about salaries, compensation, current leadership, funding, stock prices, recent news,
latest products/models, hiring, or other time-sensitive external facts are DYNAMIC.

Questions about concepts, definitions, explanations, comparisons of ideas, or how things work
are STABLE.

Question: {question}
Answer ONLY one word: DYNAMIC or STABLE
Answer:"""


class DocumentCoverage(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class QuestionNature(str, Enum):
    STABLE = "stable"
    DYNAMIC = "dynamic"


@dataclass(frozen=True)
class ResponseRoute:
    coverage: DocumentCoverage
    doc_chunks: list[RetrievedChunk]
    search_results: list[SearchResult]
    documents_used: bool
    web_search_used: bool
    general_knowledge_used: bool
    web_search_unavailable: bool = False
    document_access: bool = False


async def resolve_response_route(
    provider: LLMProvider,
    question: str,
    doc_chunks: list[RetrievedChunk],
) -> ResponseRoute:
    """Choose the best information sources after retrieval.

    Document-intent questions always use retrieved chunks when available.
    """
    doc_intent = is_document_intent_query(question)
    document_access = is_document_access_query(question)

    if doc_chunks and (doc_intent or document_access):
        logger.info(
            "Response route: document-intent fast path (chunks=%d access=%s)",
            len(doc_chunks),
            document_access,
        )
        return ResponseRoute(
            coverage=DocumentCoverage.FULL,
            doc_chunks=doc_chunks,
            search_results=[],
            documents_used=True,
            web_search_used=False,
            general_knowledge_used=False,
            document_access=document_access,
        )

    if doc_intent and not doc_chunks:
        logger.warning(
            "Response route: document intent but no chunks — skipping web/general fallback"
        )
        return ResponseRoute(
            coverage=DocumentCoverage.NONE,
            doc_chunks=[],
            search_results=[],
            documents_used=False,
            web_search_used=False,
            general_knowledge_used=False,
            document_access=document_access,
        )

    if doc_chunks:
        top_score = max(chunk.score for chunk in doc_chunks)
        if top_score >= HIGH_CONFIDENCE_CHUNK_SCORE:
            logger.info(
                "Response route: high-confidence retrieval fast path (score=%.2f, chunks=%d)",
                top_score,
                len(doc_chunks),
            )
            return ResponseRoute(
                coverage=DocumentCoverage.FULL,
                doc_chunks=doc_chunks,
                search_results=[],
                documents_used=True,
                web_search_used=False,
                general_knowledge_used=False,
            )

    coverage = await _assess_document_coverage(provider, question, doc_chunks)

    # Meta upload/visibility questions — never drop docs for coverage NONE + web search.
    if doc_chunks and is_document_access_query(question):
        logger.info(
            "Response route: document access after coverage=%s (chunks=%d)",
            coverage.value,
            len(doc_chunks),
        )
        return ResponseRoute(
            coverage=DocumentCoverage.FULL,
            doc_chunks=doc_chunks,
            search_results=[],
            documents_used=True,
            web_search_used=False,
            general_knowledge_used=False,
            document_access=True,
        )

    if coverage == DocumentCoverage.FULL:
        logger.info("Response route: documents only (coverage=full, chunks=%d)", len(doc_chunks))
        return ResponseRoute(
            coverage=coverage,
            doc_chunks=doc_chunks,
            search_results=[],
            documents_used=True,
            web_search_used=False,
            general_knowledge_used=False,
        )

    # Heuristic nature is free — use it to decide whether to start search early.
    heuristic = heuristic_question_nature(question)
    search_task: asyncio.Task | None = None
    if heuristic == "dynamic":
        search_task = asyncio.create_task(SearchService.search(question))

    nature = await _resolve_question_nature(provider, question, coverage, heuristic=heuristic)

    search_results: list[SearchResult] = []
    web_search_used = False
    general_knowledge_used = False
    web_search_unavailable = False

    if nature == QuestionNature.DYNAMIC:
        if search_task is None:
            search_results = await SearchService.search(question)
        else:
            search_results = await search_task
        if search_results:
            web_search_used = True
        else:
            web_search_unavailable = True
            general_knowledge_used = True
            logger.info("Response route: web unavailable, falling back to general knowledge")
    else:
        if search_task is not None:
            search_task.cancel()
            try:
                await search_task
            except asyncio.CancelledError:
                pass
        general_knowledge_used = True

    use_doc_chunks = doc_chunks if coverage in (DocumentCoverage.FULL, DocumentCoverage.PARTIAL) else []
    if doc_chunks and doc_intent:
        use_doc_chunks = doc_chunks
    documents_used = bool(use_doc_chunks)

    logger.info(
        "Response route: coverage=%s nature=%s docs=%s web=%s gk=%s",
        coverage.value,
        nature.value,
        documents_used,
        web_search_used,
        general_knowledge_used,
    )

    return ResponseRoute(
        coverage=coverage,
        doc_chunks=use_doc_chunks,
        search_results=search_results,
        documents_used=documents_used,
        web_search_used=web_search_used,
        general_knowledge_used=general_knowledge_used,
        web_search_unavailable=web_search_unavailable,
    )


async def _assess_document_coverage(
    provider: LLMProvider,
    question: str,
    doc_chunks: list[RetrievedChunk],
) -> DocumentCoverage:
    if not doc_chunks:
        return DocumentCoverage.NONE

    excerpts = _format_excerpts_for_assessment(doc_chunks)
    try:
        decision = await provider.fast_complete(
            [{"role": "user", "content": COVERAGE_PROMPT.format(question=question, excerpts=excerpts)}],
            max_tokens=8,
        )
        normalized = decision.strip().upper()
        if normalized.startswith("FULL"):
            return DocumentCoverage.FULL
        if normalized.startswith("PARTIAL"):
            return DocumentCoverage.PARTIAL
        if normalized.startswith("NONE"):
            return DocumentCoverage.NONE
    except Exception:
        logger.exception("Document coverage assessment failed — defaulting to NONE")

    return DocumentCoverage.NONE


async def _resolve_question_nature(
    provider: LLMProvider,
    question: str,
    coverage: DocumentCoverage,
    *,
    heuristic: str | None = None,
) -> QuestionNature:
    # Partial document coverage often means missing external entities — prefer LLM over
    # stable heuristics like "compare" that would skip web search incorrectly.
    if coverage == DocumentCoverage.PARTIAL:
        if heuristic == "dynamic":
            return QuestionNature.DYNAMIC
        if heuristic == "stable":
            return QuestionNature.STABLE
        try:
            decision = await provider.fast_complete(
                [{"role": "user", "content": NATURE_PROMPT.format(question=question)}],
                max_tokens=8,
            )
            if decision.strip().upper().startswith("DYNAMIC"):
                return QuestionNature.DYNAMIC
        except Exception:
            logger.exception("Question nature classification failed — defaulting to STABLE")
        return QuestionNature.STABLE

    if heuristic == "dynamic":
        return QuestionNature.DYNAMIC
    if heuristic == "stable":
        return QuestionNature.STABLE

    # Recompute if caller did not supply a heuristic.
    if heuristic is None:
        heuristic = heuristic_question_nature(question)
        if heuristic == "dynamic":
            return QuestionNature.DYNAMIC
        if heuristic == "stable":
            return QuestionNature.STABLE

    try:
        decision = await provider.fast_complete(
            [{"role": "user", "content": NATURE_PROMPT.format(question=question)}],
            max_tokens=8,
        )
        if decision.strip().upper().startswith("DYNAMIC"):
            return QuestionNature.DYNAMIC
    except Exception:
        logger.exception("Question nature classification failed — defaulting to STABLE")

    return QuestionNature.STABLE


def _format_excerpts_for_assessment(chunks: list[RetrievedChunk]) -> str:
    sections: list[str] = []
    for i, chunk in enumerate(chunks[:MAX_CHUNKS_FOR_ASSESSMENT], start=1):
        heading = f" — {chunk.section_heading}" if chunk.section_heading else ""
        page = f", p.{chunk.page_number}" if chunk.page_number else ""
        content = chunk.content
        if len(content) > MAX_CHUNK_CHARS:
            content = content[:MAX_CHUNK_CHARS].rstrip() + "…"
        sections.append(f"[{i}] {chunk.filename}{heading}{page}\n{content}")
    return "\n\n".join(sections)


def append_sources_section(content: str, route: ResponseRoute) -> str:
    """Ensure every routed response ends with a compact Sources Used section."""
    if not content.strip():
        return content

    if "## Sources Used" in content or "**Sources Used**" in content:
        return content

    lines = ["", "## Sources Used", ""]
    if route.documents_used:
        lines.append("📄 Uploaded Documents")
    if route.general_knowledge_used:
        lines.append("🧠 General Knowledge")
    if route.web_search_used:
        lines.append("🌐 Internet")

    if len(lines) <= 3:
        return content

    stripped = content.rstrip()
    return f"{stripped}\n" + "\n".join(lines)
