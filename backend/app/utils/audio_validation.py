"""Audio upload validation for speech transcription."""

from __future__ import annotations

ALLOWED_AUDIO_MIMES = frozenset(
    {
        "audio/webm",
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/ogg",
        "audio/flac",
        "video/webm",
    }
)

ALLOWED_AUDIO_EXTENSIONS = frozenset(
    {"webm", "wav", "mp3", "mpeg", "mp4", "m4a", "ogg", "flac", "opus"}
)


def validate_audio_upload(
    data: bytes,
    filename: str,
    content_type: str | None,
) -> str:
    if not data:
        raise ValueError("Audio file is empty.")

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime = (content_type or "").split(";")[0].strip().lower()

    if mime in ALLOWED_AUDIO_MIMES:
        return mime
    if ext in ALLOWED_AUDIO_EXTENSIONS:
        if ext in {"webm", "opus"}:
            return "audio/webm"
        if ext in {"mp3", "mpeg"}:
            return "audio/mpeg"
        if ext in {"m4a", "mp4"}:
            return "audio/mp4"
        return f"audio/{ext}"

    raise ValueError(
        "Unsupported audio format. Record again using your browser microphone."
    )
