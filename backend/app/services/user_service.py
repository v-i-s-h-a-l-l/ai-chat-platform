from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate


class UserService:
    @staticmethod
    def update_preferences(db: Session, user: User, data: UserUpdate) -> User:
        fields_set = data.model_fields_set
        if "preferred_llm_model" not in fields_set:
            return user
        return UserRepository.update_preferred_model(db, user, data.preferred_llm_model)

    @staticmethod
    def get_user(db: Session, user_id: UUID) -> User:
        user = UserRepository.get_by_id(db, user_id)
        if user is None:
            raise ValueError("User not found")
        return user
