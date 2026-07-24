import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import User
from app.providers.impl.qdrant_store import get_vector_store
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.model_resolver import normalize_model_id
from app.utils.file_storage import FileStorage

logger = logging.getLogger(__name__)


class ProjectService:
    @staticmethod
    def create_project(db: Session, user_id: UUID, data: ProjectCreate) -> Project:
        user = db.query(User).filter(User.id == user_id).first()
        llm_model = normalize_model_id(data.llm_model) or (
            normalize_model_id(user.preferred_llm_model) if user else None
        )
        return ProjectRepository.create(
            db=db,
            user_id=user_id,
            name=data.name,
            description=data.description,
            system_prompt=data.system_prompt,
            llm_model=llm_model,
        )

    @staticmethod
    def list_projects(db: Session, user_id: UUID) -> list[Project]:
        return ProjectRepository.list_by_user(db, user_id)

    @staticmethod
    def get_project(db: Session, project_id: UUID, user_id: UUID, *, touch: bool = True) -> Project:
        project = ProjectRepository.get_by_id(db, project_id, user_id)
        if project is None:
            raise ValueError("Project not found")
        if touch:
            project = ProjectRepository.touch_last_accessed(db, project)
        return project

    @staticmethod
    def update_project(
        db: Session, project_id: UUID, user_id: UUID, data: ProjectUpdate
    ) -> Project:
        project = ProjectService.get_project(db, project_id, user_id, touch=False)
        if data.name is None and data.is_pinned is None and "llm_model" not in data.model_fields_set:
            return project
        return ProjectRepository.update(
            db,
            project,
            name=data.name,
            is_pinned=data.is_pinned,
            llm_model=data.llm_model if "llm_model" in data.model_fields_set else None,
            llm_model_set="llm_model" in data.model_fields_set,
        )

    @staticmethod
    def duplicate_project(db: Session, project_id: UUID, user_id: UUID) -> Project:
        source = ProjectService.get_project(db, project_id, user_id, touch=False)
        copy_name = source.name if source.name.endswith(" (Copy)") else f"{source.name} (Copy)"
        return ProjectRepository.create(
            db=db,
            user_id=user_id,
            name=copy_name[:255],
            description=source.description,
            system_prompt=source.system_prompt,
            llm_model=source.llm_model,
        )

    @staticmethod
    async def delete_project(db: Session, project_id: UUID, user_id: UUID) -> None:
        project = ProjectService.get_project(db, project_id, user_id, touch=False)
        docs = DocumentRepository.list_by_project(db, project_id)
        storage = FileStorage()

        for doc in docs:
            if doc.storage_path:
                await storage.delete(doc.storage_path)

        try:
            await get_vector_store().delete_project(project_id)
        except Exception:
            logger.exception("Qdrant cleanup failed for project %s — continuing DB delete", project_id)

        storage.delete_project_dir(project_id)
        ProjectRepository.delete(db, project)
