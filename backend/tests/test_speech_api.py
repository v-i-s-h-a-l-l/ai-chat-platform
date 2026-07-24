from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_transcribe():
    with patch(
        "app.routes.speech._stt_service.transcribe",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


def test_transcribe_success(api_client, mock_transcribe):
    mock_transcribe.return_value = "Hello from voice"

    response = api_client.post(
        "/speech/transcribe",
        files={"file": ("recording.webm", b"fake-audio-bytes", "audio/webm")},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "Hello from voice"}
    mock_transcribe.assert_awaited_once()


def test_transcribe_empty_file(api_client, mock_transcribe):
    response = api_client.post(
        "/speech/transcribe",
        files={"file": ("recording.webm", b"", "audio/webm")},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 400
    mock_transcribe.assert_not_called()


def test_transcribe_requires_auth():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as unauth_client:
        response = unauth_client.post(
            "/speech/transcribe",
            files={"file": ("recording.webm", b"audio", "audio/webm")},
        )
    assert response.status_code == 401


def test_transcribe_service_error(api_client, mock_transcribe):
    mock_transcribe.side_effect = ValueError("No speech detected. Please try again.")

    response = api_client.post(
        "/speech/transcribe",
        files={"file": ("recording.webm", b"fake-audio-bytes", "audio/webm")},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 400
    assert "no speech" in response.json()["detail"].lower()
