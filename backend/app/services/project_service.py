from uuid import UUID

from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate


class ProjectService:
    @staticmethod
    def create_project(db: Session, user_id: UUID, data: ProjectCreate) -> Project:
        return ProjectRepository.create(
            db=db,
            user_id=user_id,
            name=data.name,
            description=data.description,
            system_prompt=data.system_prompt,
        )

    @staticmethod
    def list_projects(db: Session, user_id: UUID) -> list[Project]:
        return ProjectRepository.list_by_user(db, user_id)

    @staticmethod
    def get_project(db: Session, project_id: UUID, user_id: UUID) -> Project:
        project = ProjectRepository.get_by_id(db, project_id, user_id)
        if project is None:
            raise ValueError("Project not found")
        return project

    @staticmethod
    def delete_project(db: Session, project_id: UUID, user_id: UUID) -> None:
        project = ProjectService.get_project(db, project_id, user_id)
        ProjectRepository.delete(db, project)
