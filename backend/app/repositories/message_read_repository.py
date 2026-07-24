"""Read-side queries for chat messages (CQRS-lite).

Writes continue to go through ChatRepository.create().
Reads for the messages API use this repository and MessageReadModel only,
so list endpoints never depend on write-side entity loading patterns.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.read_models.message_read import MessageReadModel
from app.repositories.chat_repository import DEFAULT_PAGE_LIMIT


class MessageReadRepository:
    @staticmethod
    def list_by_project(
        db: Session,
        project_id: UUID,
        *,
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
    ) -> list[MessageReadModel]:
        """Paginated chronological history for the UI (read model only)."""
        stmt = (
            select(
                ChatMessage.id,
                ChatMessage.project_id,
                ChatMessage.role,
                ChatMessage.content,
                ChatMessage.created_at,
                ChatMessage.web_search_used,
                ChatMessage.documents_used,
            )
            .where(ChatMessage.project_id == project_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = db.execute(stmt).all()
        return [
            MessageReadModel(
                id=row.id,
                project_id=row.project_id,
                role=row.role,
                content=row.content,
                created_at=row.created_at,
                web_search_used=bool(row.web_search_used),
                documents_used=bool(row.documents_used),
            )
            for row in rows
        ]

    @staticmethod
    def count_by_project(db: Session, project_id: UUID) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(ChatMessage).where(
            ChatMessage.project_id == project_id
        )
        return int(db.execute(stmt).scalar_one())
