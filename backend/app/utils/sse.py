"""SSE wire-format serialization for chat stream domain events.

This is the only place that knows about the `event: ...\\ndata: ...` format —
ChatService yields plain domain events and stays transport-agnostic.
"""

import json

from app.services.chat_events import ChatStreamEvent, DoneEvent, ErrorEvent, MetaEvent, TokenEvent
from app.utils.serializers import serialize_message


def format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def serialize_chat_event(event: ChatStreamEvent) -> str:
    if isinstance(event, MetaEvent):
        return format_sse(
            "meta",
            {
                "user_message": serialize_message(event.user_message).model_dump(mode="json"),
                "web_search_used": event.web_search_used,
                "documents_used": event.documents_used,
                "retrieval_degraded": event.retrieval_degraded,
            },
        )
    if isinstance(event, TokenEvent):
        return format_sse("token", {"content": event.content})
    if isinstance(event, DoneEvent):
        return format_sse(
            "done",
            {
                "assistant_message": serialize_message(event.assistant_message).model_dump(
                    mode="json"
                ),
                "web_search_used": event.web_search_used,
                "documents_used": event.documents_used,
                "retrieval_degraded": event.retrieval_degraded,
            },
        )
    if isinstance(event, ErrorEvent):
        return format_sse("error", {"detail": event.detail})
    raise TypeError(f"Unknown chat stream event: {event!r}")
