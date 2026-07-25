from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.sarvam_stt import SarvamSttService, _build_form_data, _parse_sarvam_error


def test_build_form_data_omits_empty_language_code():
    with patch("app.services.sarvam_stt.settings") as mock_settings:
        mock_settings.sarvam_stt_model = "saaras:v3"
        mock_settings.sarvam_stt_mode = "transcribe"
        mock_settings.sarvam_stt_language_code = ""

        assert _build_form_data() == {
            "model": "saaras:v3",
            "mode": "transcribe",
        }


def test_build_form_data_includes_language_code_when_set():
    with patch("app.services.sarvam_stt.settings") as mock_settings:
        mock_settings.sarvam_stt_model = "saaras:v3"
        mock_settings.sarvam_stt_mode = "transcribe"
        mock_settings.sarvam_stt_language_code = "en-IN"

        assert _build_form_data() == {
            "model": "saaras:v3",
            "mode": "transcribe",
            "language_code": "en-IN",
        }


def test_parse_sarvam_error_status_specific():
    response = MagicMock(spec=httpx.Response)
    response.status_code = 403
    assert _parse_sarvam_error(response) == "Invalid Sarvam API key."

    response.status_code = 422
    assert _parse_sarvam_error(response) == "Audio format not accepted — try again."


def test_parse_sarvam_error_json_message():
    response = MagicMock(spec=httpx.Response)
    response.status_code = 400
    response.json.return_value = {
        "error": {"message": "Invalid model parameter"},
    }
    assert _parse_sarvam_error(response) == "Invalid model parameter"


@pytest.mark.asyncio
async def test_transcribe_sends_saaras_v3_and_mode():
    service = SarvamSttService()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"transcript": "hello world"}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with (
        patch("app.services.sarvam_stt.settings") as mock_settings,
        patch(
            "app.services.sarvam_stt.get_async_http_client",
            return_value=mock_client,
        ),
    ):
        mock_settings.sarvam_api_key = "test-key"
        mock_settings.sarvam_stt_model = "saaras:v3"
        mock_settings.sarvam_stt_mode = "transcribe"
        mock_settings.sarvam_stt_language_code = ""
        mock_settings.sarvam_stt_connect_timeout = 3.0
        mock_settings.sarvam_stt_read_timeout = 30.0

        text = await service.transcribe(b"audio-bytes", "recording.webm", "audio/webm")

    assert text == "hello world"
    mock_client.post.assert_awaited_once()
    call_kwargs = mock_client.post.await_args.kwargs
    assert call_kwargs["data"] == {"model": "saaras:v3", "mode": "transcribe"}
    assert call_kwargs["headers"] == {"api-subscription-key": "test-key"}
