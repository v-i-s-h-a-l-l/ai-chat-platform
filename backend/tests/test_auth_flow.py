"""Auth flow tests — register, login, refresh without live Groq/Qdrant."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.auth import UserLogin, UserRegister
from app.services.auth import AuthService
from app.utils.security import hash_password, verify_password


@pytest.fixture
def db_session():
    return MagicMock()


def test_register_user_rejects_duplicate_email(db_session):
    existing = MagicMock()
    with patch(
        "app.services.auth.UserRepository.get_by_email", return_value=existing
    ):
        with pytest.raises(ValueError, match="Email already registered"):
            AuthService.register_user(
                db_session,
                UserRegister(
                    name="Test",
                    email="dup@example.com",
                    password="SecurePass123!",
                ),
            )


def test_register_user_creates_account(db_session):
    with patch("app.services.auth.UserRepository.get_by_email", return_value=None):
        with patch("app.services.auth.UserRepository.create") as mock_create:
            mock_create.return_value = MagicMock(email="new@example.com")
            user = AuthService.register_user(
                db_session,
                UserRegister(
                    name="New User",
                    email="new@example.com",
                    password="SecurePass123!",
                ),
            )
            assert user.email == "new@example.com"
            mock_create.assert_called_once()


def test_authenticate_user_rejects_bad_password(db_session):
    user = MagicMock()
    user.hashed_password = hash_password("correct-password")
    with patch("app.services.auth.UserRepository.get_by_email", return_value=user):
        with pytest.raises(ValueError, match="Invalid email or password"):
            AuthService.authenticate_user(
                db_session,
                UserLogin(email="user@example.com", password="wrong-password"),
            )


def test_authenticate_user_accepts_valid_credentials(db_session):
    password = "SecurePass123!"
    user = MagicMock()
    user.hashed_password = hash_password(password)
    with patch("app.services.auth.UserRepository.get_by_email", return_value=user):
        result = AuthService.authenticate_user(
            db_session,
            UserLogin(email="user@example.com", password=password),
        )
        assert result is user


def test_create_session_returns_tokens(db_session):
    user = MagicMock()
    user.id = uuid4()
    with patch("app.services.auth.create_access_token", return_value="access"):
        with patch("app.services.auth.generate_refresh_token", return_value="refresh"):
            with patch("app.services.auth.RefreshTokenRepository.create") as mock_store:
                access, refresh = AuthService.create_session(db_session, user)
                assert access == "access"
                assert refresh == "refresh"
                mock_store.assert_called_once()


def test_refresh_session_rotates_tokens(db_session):
    user_id = uuid4()
    stored = MagicMock(user_id=user_id)
    user = MagicMock(id=user_id)
    with patch("app.services.auth.RefreshTokenRepository.get_valid", return_value=stored):
        with patch("app.services.auth.UserRepository.get_by_id", return_value=user):
            with patch("app.services.auth.RefreshTokenRepository.revoke") as mock_revoke:
                with patch.object(
                    AuthService,
                    "create_session",
                    return_value=("new-access", "new-refresh"),
                ):
                    access, refresh, refreshed_user = AuthService.refresh_session(
                        db_session, "raw-refresh-token"
                    )
                    assert access == "new-access"
                    assert refresh == "new-refresh"
                    assert refreshed_user is user
                    mock_revoke.assert_called_once_with(db_session, stored)


def test_refresh_session_rejects_invalid_token(db_session):
    with patch("app.services.auth.RefreshTokenRepository.get_valid", return_value=None):
        with pytest.raises(ValueError, match="Invalid or expired refresh token"):
            AuthService.refresh_session(db_session, "bad-token")


def test_password_hash_roundtrip():
    hashed = hash_password("SecurePass123!")
    assert verify_password("SecurePass123!", hashed)
    assert not verify_password("wrong", hashed)
