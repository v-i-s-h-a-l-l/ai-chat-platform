"""Single source of truth for ORM -> API response serialization.

Keeping this in one place avoids the message/project shape being rebuilt
slightly differently in routes, services, and the SSE layer.
"""

from app.models.chat_message import ChatMessage
from app.models.project import Project
from app.schemas.chat import ChatMessageResponse
from app.schemas.project import ProjectResponse


def serialize_project(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        system_prompt=project.system_prompt,
        created_at=project.created_at.isoformat(),
    )


def serialize_message(message: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at.isoformat(),
        web_search_used=getattr(message, "web_search_used", False),
        documents_used=getattr(message, "documents_used", False),
    )
