import logging
from typing import Any

import httpx

from app.config import settings
from app.utils.audio_validation import validate_audio_upload
from app.utils.http_client import get_async_http_client

logger = logging.getLogger(__name__)


class SarvamSttService:
    """Sarvam AI Speech-to-Text — isolated from chat/RAG pipeline."""

    BASE_URL = "https://api.sarvam.ai/speech-to-text"

    async def transcribe(
        self,
        data: bytes,
        filename: str,
        content_type: str | None,
    ) -> str:
        api_key = settings.sarvam_api_key.strip()
        if not api_key:
            raise ValueError("Speech transcription is not configured on the server.")

        mime = validate_audio_upload(data, filename, content_type)

        headers = {"api-subscription-key": api_key}
        files = {"file": (filename, data, mime)}
        form_data = {
            "model": settings.sarvam_stt_model,
            "language_code": settings.sarvam_stt_language_code,
        }

        timeout = httpx.Timeout(
            connect=settings.sarvam_stt_connect_timeout,
            read=settings.sarvam_stt_read_timeout,
            write=10.0,
            pool=5.0,
        )

        try:
            client = get_async_http_client()
            response = await client.post(
                self.BASE_URL,
                headers=headers,
                files=files,
                data=form_data,
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise ValueError(
                "Transcription timed out. Please try a shorter recording."
            ) from exc
        except httpx.TransportError as exc:
            logger.warning("Sarvam STT transport error: %s", exc)
            raise ValueError(
                "Could not reach the transcription service. Check your connection."
            ) from exc

        if response.status_code >= 400:
            logger.warning(
                "Sarvam STT HTTP %s: %s",
                response.status_code,
                response.text[:500],
            )
            raise ValueError(
                "Transcription failed. Please try recording again."
            )

        payload: dict[str, Any] = response.json()
        transcript = (payload.get("transcript") or "").strip()
        if not transcript:
            raise ValueError("No speech detected. Please try again.")

        return transcript
