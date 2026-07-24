from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.models.chat_message import ChatMessage
from app.services.chat_events import DoneEvent, MetaEvent, TokenEvent


async def _mock_stream(*_args, **_kwargs):
    user_msg = ChatMessage(
        id=uuid4(),
        project_id=uuid4(),
        role="user",
        content="Hello",
        web_search_used=False,
        documents_used=False,
        created_at=datetime.now(timezone.utc),
    )
    assistant_msg = ChatMessage(
        id=uuid4(),
        project_id=user_msg.project_id,
        role="assistant",
        content="Hi there",
        web_search_used=False,
        documents_used=False,
        created_at=datetime.now(timezone.utc),
    )
    yield MetaEvent(user_message=user_msg, web_search_used=False, documents_used=False)
    yield TokenEvent(content="Hi ")
    yield TokenEvent(content="there")
    yield DoneEvent(
        assistant_message=assistant_msg,
        web_search_used=False,
        documents_used=False,
    )


def test_chat_stream_returns_sse(api_client):
    project_id = uuid4()

    with patch(
        "app.routes.projects.ChatService.stream_message",
        side_effect=_mock_stream,
    ):
        response = api_client.post(
            f"/projects/{project_id}/chat/stream",
            json={"message": "Hello"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "Cache-Control" in response.headers
    body = response.text
    assert "event:" in body or "data:" in body


def test_chat_stream_requires_auth():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        response = client.post(
            f"/projects/{uuid4()}/chat/stream",
            json={"message": "Hello"},
        )
    assert response.status_code == 401
