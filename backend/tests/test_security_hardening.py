import pytest
from fastapi import HTTPException

from app.utils.errors import GENERIC_CLIENT_ERROR, sanitize_error_for_client
from app.utils.mime_validation import detect_mime
from app.utils.upload_reader import read_upload_capped


def test_detect_pdf_mime():
    data = b"%PDF-1.4\n%...\n"
    assert detect_mime(data, "report.pdf", "application/pdf") == "application/pdf"


def test_detect_text_mime():
    data = b"Hello world\nThis is plain text.\n"
    assert detect_mime(data, "notes.txt", "text/plain") == "text/plain"


def test_reject_mime_spoof():
    data = b"%PDF-1.4\nfake"
    with pytest.raises(ValueError, match="does not match"):
        detect_mime(data, "report.pdf", "text/plain")


def test_reject_empty_file():
    with pytest.raises(ValueError, match="Empty"):
        detect_mime(b"", "empty.txt", "text/plain")


def test_sanitize_error_hides_internal_details():
    message = sanitize_error_for_client(
        RuntimeError("secret path C:/keys/token"),
        context="unit-test",
        public_message=GENERIC_CLIENT_ERROR,
        allow_value_error=False,
    )
    assert message == GENERIC_CLIENT_ERROR
    assert "secret" not in message


def test_sanitize_error_keeps_value_error():
    message = sanitize_error_for_client(
        ValueError("Project not found"),
        context="unit-test",
    )
    assert message == "Project not found"


class _FakeUpload:
    def __init__(self, payload: bytes, chunk_size: int = 8):
        self._payload = payload
        self._offset = 0
        self._chunk_size = chunk_size

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._payload):
            return b""
        end = len(self._payload) if size < 0 else min(self._offset + size, len(self._payload))
        chunk = self._payload[self._offset:end]
        self._offset = end
        return chunk


@pytest.mark.asyncio
async def test_read_upload_capped_rejects_oversized():
    upload = _FakeUpload(b"x" * 100)
    with pytest.raises(HTTPException) as exc:
        await read_upload_capped(upload, max_bytes=50)
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_read_upload_capped_accepts_within_limit():
    upload = _FakeUpload(b"hello-world")
    data = await read_upload_capped(upload, max_bytes=50)
    assert data == b"hello-world"
