import logging
import shutil
from pathlib import Path
from uuid import UUID

import aiofiles

from app.config import settings

logger = logging.getLogger(__name__)


class FileStorage:
    """Local filesystem storage for uploaded documents (source of truth)."""

    def __init__(self, base_path: str | None = None) -> None:
        self._base = Path(base_path or settings.document_storage_path)

    def _project_dir(self, project_id: UUID) -> Path:
        path = self._base / str(project_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def save(self, project_id: UUID, document_id: UUID, filename: str, data: bytes) -> str:
        project_dir = self._project_dir(project_id)
        safe_name = Path(filename).name
        dest = project_dir / f"{document_id}_{safe_name}"
        async with aiofiles.open(dest, "wb") as f:
            await f.write(data)
        logger.info("Stored document: %s (%d bytes)", dest, len(data))
        return str(dest)

    async def read(self, storage_path: str) -> bytes:
        async with aiofiles.open(storage_path, "rb") as f:
            return await f.read()

    async def delete(self, storage_path: str) -> None:
        path = Path(storage_path)
        if path.exists():
            path.unlink()

    def delete_project_dir(self, project_id: UUID) -> None:
        path = self._base / str(project_id)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            logger.info("Removed project storage directory: %s", path)

    def get_path(self, project_id: UUID, document_id: UUID, filename: str) -> str:
        safe_name = Path(filename).name
        return str(self._project_dir(project_id) / f"{document_id}_{safe_name}")
