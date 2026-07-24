from uuid import UUID

from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage

DEFAULT_HISTORY_LIMIT = 6
DEFAULT_PAGE_LIMIT = 200


class ChatRepository:
    @staticmethod
    def list_by_project(
        db: Session,
        project_id: UUID,
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
    ) -> list[ChatMessage]:
        """Paginated, chronological (oldest-first) fetch — used by the messages endpoint."""
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.project_id == project_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_recent(
        db: Session, project_id: UUID, limit: int = DEFAULT_HISTORY_LIMIT
    ) -> list[ChatMessage]:
        """Fetch only the most recent `limit` messages (chronological order) — used to build
        LLM context without loading the entire conversation on every turn."""
        rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.project_id == project_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(rows))

    @staticmethod
    def create(
        db: Session,
        project_id: UUID,
        role: str,
        content: str,
        web_search_used: bool = False,
        documents_used: bool = False,
    ) -> ChatMessage:
        message = ChatMessage(
            project_id=project_id,
            role=role,
            content=content,
            web_search_used=web_search_used,
            documents_used=documents_used,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def get_by_id(
        db: Session, project_id: UUID, message_id: UUID
    ) -> ChatMessage | None:
        return (
            db.query(ChatMessage)
            .filter(
                ChatMessage.id == message_id,
                ChatMessage.project_id == project_id,
            )
            .first()
        )
