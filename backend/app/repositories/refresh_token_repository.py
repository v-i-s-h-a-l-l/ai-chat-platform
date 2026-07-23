from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    @staticmethod
    def create(db: Session, user_id: UUID, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        db.add(token)
        db.commit()
        return token

    @staticmethod
    def get_valid(db: Session, token_hash: str) -> RefreshToken | None:
        return (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )

    @staticmethod
    def get_by_hash(db: Session, token_hash: str) -> RefreshToken | None:
        return db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    @staticmethod
    def revoke(db: Session, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(timezone.utc)
        db.commit()
