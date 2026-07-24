import pytest

from app.utils.audio_validation import validate_audio_upload


def test_validate_audio_webm():
    mime = validate_audio_upload(b"RIFF", "recording.webm", "audio/webm")
    assert mime == "audio/webm"


def test_validate_audio_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        validate_audio_upload(b"", "recording.webm", "audio/webm")


def test_validate_audio_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported"):
        validate_audio_upload(b"data", "notes.txt", "text/plain")
