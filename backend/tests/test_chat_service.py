"""Chat stream meta flags — retrieval degradation visibility."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.chat_message import ChatMessage
from app.models.project import Project
from app.models.user import User
from app.providers.types import RetrievedChunk
from app.services.chat_events import DoneEvent, MetaEvent, TokenEvent
from app.services.chat_service import ChatService
from app.services.rag_context import RagContextResult
from app.services.response_router import DocumentCoverage, ResponseRoute


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        project_id=uuid4(),
        filename="paper.pdf",
        content="Transformer architecture overview.",
        chunk_index=0,
        page_number=1,
        section_heading="Intro",
        score=0.91,
    )


class FakeProvider:
    async def stream(self, messages, model=None):
        yield "Answer from docs."

    async def complete(self, messages, model=None):
        return "Answer from docs."

    async def fast_complete(self, messages, max_tokens=8):
        return "FULL"


@pytest.mark.asyncio
async def test_stream_meta_includes_retrieval_degraded_flag():
    project_id = uuid4()
    user_id = uuid4()
    project = Project(
        id=project_id,
        user_id=user_id,
        name="Test",
        description="",
        system_prompt="You are helpful.",
    )
    user = User(id=user_id, email="u@example.com", name="User", hashed_password="x")
    route = ResponseRoute(
        coverage=DocumentCoverage.FULL,
        doc_chunks=[],
        search_results=[],
        documents_used=False,
        web_search_used=False,
        general_knowledge_used=True,
    )

    async def fake_load_context(_project_id, _user_id):
        return project, user, []

    async def fake_persist_message(_project_id, role, content, **kwargs):
        return ChatMessage(
            id=uuid4(),
            project_id=project_id,
            role=role,
            content=content,
            web_search_used=kwargs.get("web_search_used", False),
            documents_used=kwargs.get("documents_used", False),
        )

    with patch.object(ChatService, "_load_context", side_effect=fake_load_context):
        with patch.object(ChatService, "_persist_message", side_effect=fake_persist_message):
            with patch(
                "app.services.chat_service.resolve_rag_context",
                return_value=RagContextResult(chunks=[], has_chunks=False, retrieval_degraded=True),
            ):
                with patch(
                    "app.services.chat_service.resolve_response_route",
                    return_value=route,
                ):
                    with patch("app.services.chat_service.settings.response_routing_enabled", True):
                        events = []
                        async for event in ChatService.stream_message(
                            project_id,
                            user_id,
                            "Summarize the paper",
                            FakeProvider(),
                        ):
                            events.append(event)

    meta = next(e for e in events if isinstance(e, MetaEvent))
    done = next(e for e in events if isinstance(e, DoneEvent))
    assert meta.retrieval_degraded is True
    assert done.retrieval_degraded is True
    assert any(isinstance(e, TokenEvent) for e in events)


@pytest.mark.asyncio
async def test_stream_meta_retrieval_degraded_false_when_healthy():
    project_id = uuid4()
    user_id = uuid4()
    project = Project(
        id=project_id,
        user_id=user_id,
        name="Test",
        description="",
        system_prompt="You are helpful.",
    )
    user = User(id=user_id, email="u@example.com", name="User", hashed_password="x")
    chunks = [_chunk()]
    route = ResponseRoute(
        coverage=DocumentCoverage.FULL,
        doc_chunks=chunks,
        search_results=[],
        documents_used=True,
        web_search_used=False,
        general_knowledge_used=False,
    )

    async def fake_load_context(_project_id, _user_id):
        return project, user, []

    async def fake_persist_message(_project_id, role, content, **kwargs):
        return ChatMessage(
            id=uuid4(),
            project_id=project_id,
            role=role,
            content=content,
            web_search_used=kwargs.get("web_search_used", False),
            documents_used=kwargs.get("documents_used", False),
        )

    with patch.object(ChatService, "_load_context", side_effect=fake_load_context):
        with patch.object(ChatService, "_persist_message", side_effect=fake_persist_message):
            with patch(
                "app.services.chat_service.resolve_rag_context",
                return_value=RagContextResult(chunks=chunks, has_chunks=True, retrieval_degraded=False),
            ):
                with patch(
                    "app.services.chat_service.resolve_response_route",
                    return_value=route,
                ):
                    with patch("app.services.chat_service.settings.response_routing_enabled", True):
                        events = []
                        async for event in ChatService.stream_message(
                            project_id,
                            user_id,
                            "What is the transformer?",
                            FakeProvider(),
                        ):
                            events.append(event)

    meta = next(e for e in events if isinstance(e, MetaEvent))
    assert meta.retrieval_degraded is False
    assert meta.documents_used is True
