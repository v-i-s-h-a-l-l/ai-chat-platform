from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.document import Document


def _mock_document(project_id):
    doc = Document(
        id=uuid4(),
        project_id=project_id,
        filename="sample.pdf",
        storage_path="/tmp/sample.pdf",
        mime_type="application/pdf",
        file_size=1024,
        status="processing",
        error_message=None,
        chunk_count=0,
        created_at=datetime.now(timezone.utc),
    )
    return doc


def test_upload_document_success(api_client, mock_user):
    project_id = uuid4()
    doc = _mock_document(project_id)

    with patch(
        "app.routes.documents.DocumentService.upload_document",
        new_callable=AsyncMock,
        return_value=doc,
    ):
        response = api_client.post(
            f"/projects/{project_id}/documents",
            files={"file": ("sample.pdf", b"%PDF-1.4 test", "application/pdf")},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["document"]["filename"] == "sample.pdf"
    assert data["document"]["status"] == "processing"


def test_list_documents(api_client):
    project_id = uuid4()
    doc = _mock_document(project_id)

    with patch(
        "app.routes.documents.DocumentService.list_documents_with_recovery",
        new_callable=AsyncMock,
        return_value=[doc],
    ):
        response = api_client.get(f"/projects/{project_id}/documents")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["filename"] == "sample.pdf"


def test_delete_document(api_client):
    project_id = uuid4()
    document_id = uuid4()

    with patch(
        "app.routes.documents.DocumentService.delete_document",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = api_client.delete(
            f"/projects/{project_id}/documents/{document_id}",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

    assert response.status_code == 204


def test_upload_document_project_not_found(api_client):
    project_id = uuid4()

    with patch(
        "app.routes.documents.DocumentService.upload_document",
        new_callable=AsyncMock,
        side_effect=ValueError("Project not found"),
    ):
        response = api_client.post(
            f"/projects/{project_id}/documents",
            files={"file": ("sample.pdf", b"%PDF-1.4 test", "application/pdf")},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

    assert response.status_code == 404
