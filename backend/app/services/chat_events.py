"""Domain events yielded by ChatService.stream_message.

These carry ORM objects, not wire format — the route layer is responsible
for serializing them to SSE. This keeps transport concerns out of the
service layer.
"""

from dataclasses import dataclass

from app.models.chat_message import ChatMessage


@dataclass(frozen=True)
class MetaEvent:
    user_message: ChatMessage
    web_search_used: bool
    documents_used: bool = False
    retrieval_degraded: bool = False


@dataclass(frozen=True)
class TokenEvent:
    content: str


@dataclass(frozen=True)
class DoneEvent:
    assistant_message: ChatMessage
    web_search_used: bool
    documents_used: bool = False
    retrieval_degraded: bool = False


@dataclass(frozen=True)
class ErrorEvent:
    detail: str


ChatStreamEvent = MetaEvent | TokenEvent | DoneEvent | ErrorEvent
