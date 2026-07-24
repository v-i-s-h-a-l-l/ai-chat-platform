from unittest.mock import MagicMock, patch

from app.database import get_db
from app.main import app
from app.utils.cookies import ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE
from fastapi.testclient import TestClient


def test_register_success(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        with patch("app.routes.auth.AuthService.register_user") as mock_register:
            with TestClient(app) as client:
                response = client.post(
                    "/auth/register",
                    json={
                        "name": "New User",
                        "email": "new@example.com",
                        "password": "SecurePass123!",
                    },
                )
        assert response.status_code == 201
        assert response.json()["message"] == "User created successfully"
        mock_register.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_register_rejects_duplicate(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        with patch(
            "app.routes.auth.AuthService.register_user",
            side_effect=ValueError("Email already registered"),
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/auth/register",
                    json={
                        "name": "Dup",
                        "email": "dup@example.com",
                        "password": "SecurePass123!",
                    },
                )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_login_sets_auth_cookies(mock_db):
    user = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        with (
            patch("app.routes.auth.AuthService.authenticate_user", return_value=user),
            patch(
                "app.routes.auth.AuthService.create_session",
                return_value=("access-token", "refresh-token"),
            ),
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/auth/login",
                    json={"email": "user@example.com", "password": "SecurePass123!"},
                )
        assert response.status_code == 200
        assert ACCESS_TOKEN_COOKIE in response.cookies
        assert REFRESH_TOKEN_COOKIE in response.cookies
    finally:
        app.dependency_overrides.clear()


def test_refresh_requires_cookie(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        with TestClient(app) as client:
            response = client.post("/auth/refresh")
        assert response.status_code == 401
        assert "missing" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_users_me_returns_current_user(api_client, mock_user):
    response = api_client.get("/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_user.email
    assert data["name"] == mock_user.name


def test_users_me_requires_auth():
    with TestClient(app) as client:
        response = client.get("/users/me")
    assert response.status_code == 401
