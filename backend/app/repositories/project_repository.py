from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.project import Project


class ProjectRepository:
    @staticmethod
    def create(
        db: Session,
        user_id: UUID,
        name: str,
        description: str,
        system_prompt: str,
        llm_model: str | None = None,
    ) -> Project:
        now = datetime.now(UTC)
        project = Project(
            user_id=user_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            llm_model=llm_model,
            last_accessed_at=now,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def get_by_id(db: Session, project_id: UUID, user_id: UUID) -> Project | None:
        return (
            db.query(Project)
            .filter(Project.id == project_id, Project.user_id == user_id)
            .first()
        )

    @staticmethod
    def list_by_user(db: Session, user_id: UUID) -> list[Project]:
        return (
            db.query(Project)
            .filter(Project.user_id == user_id)
            .order_by(
                Project.is_pinned.desc(),
                Project.last_accessed_at.desc().nullslast(),
                Project.created_at.desc(),
            )
            .all()
        )

    @staticmethod
    def touch_last_accessed(db: Session, project: Project) -> Project:
        project.last_accessed_at = datetime.now(UTC)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def update(
        db: Session,
        project: Project,
        *,
        name: str | None = None,
        is_pinned: bool | None = None,
        llm_model: str | None = None,
        llm_model_set: bool = False,
    ) -> Project:
        if name is not None:
            project.name = name
        if is_pinned is not None:
            project.is_pinned = is_pinned
        if llm_model_set:
            project.llm_model = llm_model
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete(db: Session, project: Project) -> None:
        db.delete(project)
        db.commit()

    @staticmethod
    def set_active_document(
        db: Session, project_id: UUID, document_id: UUID | None
    ) -> None:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is None:
            return
        project.active_document_id = document_id
        db.commit()

    @staticmethod
    def get_active_document_id(db: Session, project_id: UUID) -> UUID | None:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is None:
            return None
        return project.active_document_id
