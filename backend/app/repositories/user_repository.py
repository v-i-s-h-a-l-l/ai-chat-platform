from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: UUID) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def create(
        db: Session,
        *,
        name: str,
        email: str,
        hashed_password: str,
    ) -> User:
        user = User(name=name, email=email, hashed_password=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_preferred_model(
        db: Session, user: User, preferred_llm_model: str | None
    ) -> User:
        user.preferred_llm_model = preferred_llm_model
        db.commit()
        db.refresh(user)
        return user
