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
    ) -> Project:
        project = Project(
            user_id=user_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
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
            .order_by(Project.created_at.desc())
            .all()
        )

    @staticmethod
    def delete(db: Session, project: Project) -> None:
        db.delete(project)
        db.commit()
