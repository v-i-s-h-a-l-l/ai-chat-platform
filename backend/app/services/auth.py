from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserLogin, UserRegister
from app.utils.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


class AuthService:
    @staticmethod
    def register_user(db: Session, data: UserRegister) -> User:
        existing = UserRepository.get_by_email(db, data.email)
        if existing:
            raise ValueError("Email already registered")

        return UserRepository.create(
            db,
            name=data.name,
            email=data.email,
            hashed_password=hash_password(data.password),
        )

    @staticmethod
    def authenticate_user(db: Session, data: UserLogin) -> User:
        user = UserRepository.get_by_email(db, data.email)
        if user is None or not verify_password(data.password, user.hashed_password):
            raise ValueError("Invalid email or password")
        return user

    @staticmethod
    def create_session(db: Session, user: User) -> tuple[str, str]:
        access_token = create_access_token(str(user.id))
        refresh_token = generate_refresh_token()

        RefreshTokenRepository.create(
            db,
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        )
        return access_token, refresh_token

    @staticmethod
    def refresh_session(db: Session, refresh_token: str) -> tuple[str, str, User]:
        token_hash = hash_refresh_token(refresh_token)
        stored = RefreshTokenRepository.get_valid(db, token_hash)

        if stored is None:
            raise ValueError("Invalid or expired refresh token")

        user = UserRepository.get_by_id(db, stored.user_id)
        if user is None:
            raise ValueError("User not found")

        RefreshTokenRepository.revoke(db, stored)
        access_token, new_refresh_token = AuthService.create_session(db, user)
        return access_token, new_refresh_token, user

    @staticmethod
    def revoke_refresh_token(db: Session, refresh_token: str | None) -> None:
        if not refresh_token:
            return

        token_hash = hash_refresh_token(refresh_token)
        stored = RefreshTokenRepository.get_by_hash(db, token_hash)
        if stored and stored.revoked_at is None:
            RefreshTokenRepository.revoke(db, stored)
