"""Project delete cleanup — Qdrant, filesystem, then DB."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.project_service import ProjectService


@pytest.mark.asyncio
async def test_delete_project_cleans_qdrant_files_and_db():
    project_id = uuid4()
    user_id = uuid4()
    doc = MagicMock(storage_path="/tmp/doc.pdf")
    project = MagicMock()
    db = MagicMock()

    mock_store = AsyncMock()
    mock_storage = MagicMock()
    mock_storage.delete = AsyncMock()

    with patch.object(ProjectService, "get_project", return_value=project):
        with patch(
            "app.services.project_service.DocumentRepository.list_by_project",
            return_value=[doc],
        ):
            with patch(
                "app.services.project_service.get_vector_store", return_value=mock_store
            ):
                with patch(
                    "app.services.project_service.FileStorage", return_value=mock_storage
                ):
                    with patch(
                        "app.services.project_service.ProjectRepository.delete"
                    ) as mock_db_delete:
                        await ProjectService.delete_project(db, project_id, user_id)

    mock_storage.delete.assert_awaited_once_with("/tmp/doc.pdf")
    mock_store.delete_project.assert_awaited_once_with(project_id)
    mock_storage.delete_project_dir.assert_called_once_with(project_id)
    mock_db_delete.assert_called_once_with(db, project)


@pytest.mark.asyncio
async def test_delete_project_continues_when_qdrant_fails():
    project_id = uuid4()
    user_id = uuid4()
    project = MagicMock()
    db = MagicMock()

    mock_store = AsyncMock()
    mock_store.delete_project.side_effect = RuntimeError("qdrant down")
    mock_storage = MagicMock()
    mock_storage.delete = AsyncMock()

    with patch.object(ProjectService, "get_project", return_value=project):
        with patch(
            "app.services.project_service.DocumentRepository.list_by_project",
            return_value=[],
        ):
            with patch(
                "app.services.project_service.get_vector_store", return_value=mock_store
            ):
                with patch(
                    "app.services.project_service.FileStorage", return_value=mock_storage
                ):
                    with patch(
                        "app.services.project_service.ProjectRepository.delete"
                    ) as mock_db_delete:
                        await ProjectService.delete_project(db, project_id, user_id)

    mock_db_delete.assert_called_once_with(db, project)
