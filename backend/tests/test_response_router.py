from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.providers.types import RetrievedChunk
from app.services.response_router import (
    DocumentCoverage,
    ResponseRoute,
    append_sources_section,
    resolve_response_route,
)


def _chunk(content: str = "Some document text about MathCo.") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        project_id=uuid4(),
        filename="mathco.pdf",
        content=content,
        chunk_index=0,
        page_number=1,
        section_heading="Overview",
        score=0.9,
    )


class FakeProvider:
    def __init__(self, coverage: str = "NONE", nature: str = "STABLE") -> None:
        self.coverage = coverage
        self.nature = nature

    async def fast_complete(self, messages, max_tokens=8):
        content = messages[0]["content"]
        if "Can these excerpts answer" in content:
            return self.coverage
        if "DYNAMIC or STABLE" in content:
            return self.nature
        return "NONE"


@pytest.mark.asyncio
async def test_full_coverage_uses_documents_only():
    provider = FakeProvider(coverage="FULL")
    chunks = [_chunk()]

    route = await resolve_response_route(provider, "What is MathCo?", chunks)

    assert route.coverage == DocumentCoverage.FULL
    assert route.documents_used is True
    assert route.web_search_used is False
    assert route.general_knowledge_used is False
    assert route.doc_chunks == chunks


@pytest.mark.asyncio
async def test_none_stable_uses_general_knowledge():
    provider = FakeProvider(coverage="NONE", nature="STABLE")

    route = await resolve_response_route(provider, "What is supervised learning?", [])

    assert route.documents_used is False
    assert route.web_search_used is False
    assert route.general_knowledge_used is True


@pytest.mark.asyncio
@patch("app.services.response_router.SearchService.search", new_callable=AsyncMock)
async def test_none_dynamic_triggers_web_search(mock_search):
    mock_search.return_value = [
        type("R", (), {"title": "T", "content": "Salary info", "url": "https://example.com"})()
    ]
    provider = FakeProvider(coverage="NONE", nature="DYNAMIC")

    route = await resolve_response_route(provider, "What is the salary at Acme?", [])

    assert route.web_search_used is True
    assert route.general_knowledge_used is False
    mock_search.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.services.response_router.SearchService.search", new_callable=AsyncMock)
async def test_dynamic_web_failure_falls_back_to_general_knowledge(mock_search):
    mock_search.return_value = []
    provider = FakeProvider(coverage="NONE", nature="DYNAMIC")

    route = await resolve_response_route(provider, "Latest funding for Acme?", [])

    assert route.web_search_used is False
    assert route.general_knowledge_used is True
    assert route.web_search_unavailable is True


@pytest.mark.asyncio
@patch("app.services.response_router.SearchService.search", new_callable=AsyncMock)
async def test_partial_dynamic_uses_documents_and_web(mock_search):
    mock_search.return_value = [
        type("R", (), {"title": "T", "content": "Yellow.ai info", "url": "https://example.com"})()
    ]
    provider = FakeProvider(coverage="PARTIAL", nature="DYNAMIC")
    chunks = [_chunk("MathCo is a data analytics company.")]

    route = await resolve_response_route(provider, "Compare MathCo with Yellow.ai", chunks)

    assert route.documents_used is True
    assert route.web_search_used is True
    assert route.doc_chunks == chunks


@pytest.mark.asyncio
async def test_partial_stable_uses_documents_and_general_knowledge():
    provider = FakeProvider(coverage="PARTIAL", nature="STABLE")
    chunks = [_chunk("MathCo uses Python.")]

    route = await resolve_response_route(
        provider, "What does MathCo use and what is supervised learning?", chunks
    )

    assert route.documents_used is True
    assert route.general_knowledge_used is True
    assert route.web_search_used is False


def test_append_sources_section_adds_badges():
    route = ResponseRoute(
        coverage=DocumentCoverage.PARTIAL,
        doc_chunks=[],
        search_results=[],
        documents_used=True,
        web_search_used=True,
        general_knowledge_used=False,
    )
    result = append_sources_section("## Answer\n\nSome text.", route)

    assert "## Sources Used" in result
    assert "📄 Uploaded Documents" in result
    assert "🌐 Internet" in result


def test_append_sources_section_skips_if_present():
    route = ResponseRoute(
        coverage=DocumentCoverage.FULL,
        doc_chunks=[_chunk()],
        search_results=[],
        documents_used=True,
        web_search_used=False,
        general_knowledge_used=False,
    )
    content = "## Answer\n\n## Sources Used\n\n📄 Uploaded Documents"
    assert append_sources_section(content, route) == content
