"""Streamed upload reading with hard size caps (DoS protection)."""

from __future__ import annotations

from fastapi import HTTPException, UploadFile, status

from app.config import settings

# Read in 64 KiB chunks so oversized uploads are aborted early.
_CHUNK_SIZE = 64 * 1024


async def read_upload_capped(
    file: UploadFile,
    *,
    max_bytes: int | None = None,
) -> bytes:
    """Read an upload into memory, aborting as soon as max_bytes is exceeded."""
    limit = max_bytes if max_bytes is not None else settings.rag_max_upload_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {settings.rag_max_upload_mb} MB",
            )
        chunks.append(chunk)

    return b"".join(chunks)
