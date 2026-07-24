from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.repositories.chat_repository import ChatRepository
from app.services.project_service import ProjectService
from app.workspace_export.engine import WorkspaceExportEngine
from app.workspace_export.models import ExportFormat


class WorkspaceExportService:
    def __init__(self, engine: WorkspaceExportEngine | None = None) -> None:
        self._engine = engine or WorkspaceExportEngine()

    def get_message_for_export(
        self,
        db: Session,
        project_id: UUID,
        message_id: UUID,
        user_id: UUID,
    ) -> tuple[ChatMessage, str | None]:
        project = ProjectService.get_project(db, project_id, user_id)
        message = ChatRepository.get_by_id(db, project_id, message_id)
        if message is None:
            raise ValueError("Message not found")
        if message.role != "assistant":
            raise ValueError("Only assistant responses can be exported")
        return message, project.name

    def list_formats(self, content: str) -> dict:
        return {
            "formats": self._engine.list_formats(content),
            "excel_supported": self._engine.supports_excel(content),
        }

    def export_message(
        self,
        db: Session,
        project_id: UUID,
        message_id: UUID,
        user_id: UUID,
        export_format: ExportFormat,
    ) -> tuple[bytes, str, str]:
        message, project_name = self.get_message_for_export(db, project_id, message_id, user_id)
        return self._engine.export(
            message.content,
            export_format,
            project_name=project_name,
        )
