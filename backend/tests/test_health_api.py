from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_checks_shape():
    with (
        patch("app.main.check_database", return_value=True),
        patch("app.main._check_redis", new_callable=AsyncMock, return_value=True),
        patch("app.main._check_qdrant", new_callable=AsyncMock, return_value=True),
    ):
        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["checks"]["database"] is True
    assert data["checks"]["redis"] is True
    assert data["checks"]["qdrant"] is True
    assert "ingestion_inline_fallback" in data


def test_health_degraded_when_redis_down():
    with (
        patch("app.main.check_database", return_value=True),
        patch("app.main._check_redis", new_callable=AsyncMock, return_value=False),
        patch("app.main._check_qdrant", new_callable=AsyncMock, return_value=True),
    ):
        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
