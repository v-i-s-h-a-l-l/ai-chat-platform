from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.config import settings
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.speech import TranscribeResponse
from app.services.sarvam_stt import SarvamSttService
from app.utils.errors import sanitize_error_for_client
from app.utils.rate_limit import limiter
from app.utils.upload_reader import read_upload_capped

router = APIRouter(prefix="/speech", tags=["speech"])

_stt_service = SarvamSttService()


@router.post("/transcribe", response_model=TranscribeResponse)
@limiter.limit(settings.rate_limit_speech)
async def transcribe_speech(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Transcribe short audio via Sarvam STT. Does not touch chat or RAG."""
    _ = current_user

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename required",
        )

    max_bytes = settings.speech_max_upload_mb * 1024 * 1024
    try:
        data = await read_upload_capped(file, max_bytes=max_bytes)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Audio exceeds maximum size of {settings.speech_max_upload_mb} MB",
            ) from exc
        raise

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is empty.",
        )

    try:
        text = await _stt_service.transcribe(data, file.filename, file.content_type)
    except ValueError as exc:
        detail = str(exc)
        if "not configured" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=sanitize_error_for_client(
                exc,
                context="Speech transcription",
                public_message="Transcription failed. Please try again.",
            ),
        ) from exc

    return TranscribeResponse(text=text)
